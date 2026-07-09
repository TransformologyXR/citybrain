from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1.zip"

REQUIRED_OUTPUTS = [
    "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json",
    "SEED_ENTITY_MANIFEST.json",
    "SEED_SOURCE_CLASS_LEDGER.csv",
    "GOLD_LAYER_MANIFEST.json",
    "DIRTY_SOURCE_LAYER_MANIFEST.json",
    "CHALLENGE_LAYER_MANIFEST.json",
    "SCENARIO_LAYER_MANIFEST.json",
    "EVENT_REPLAY_TAPE.jsonl",
    "WATCH_SEED_QUEUE.jsonl",
    "ASK_ENTITY_PROFILE_FIXTURES.jsonl",
    "CHECK_CLAIMABILITY_FIXTURES.jsonl",
    "BRIEF_PACKET_FIXTURES.jsonl",
    "SPATIAL_OVERLAY_FIXTURES.jsonl",
    "FACTORY_VALIDATION_REPORT.json",
    "BOUNDARY_AND_NO_ACTION_AUDIT.json",
    "SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

JSONL_OUTPUTS = [
    "EVENT_REPLAY_TAPE.jsonl",
    "WATCH_SEED_QUEUE.jsonl",
    "ASK_ENTITY_PROFILE_FIXTURES.jsonl",
    "CHECK_CLAIMABILITY_FIXTURES.jsonl",
    "BRIEF_PACKET_FIXTURES.jsonl",
    "SPATIAL_OVERLAY_FIXTURES.jsonl",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_jsonl(name: str) -> list[dict]:
    rows = []
    for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_seed_r1_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS"
    assert decision["input_statuses"]["r2"].startswith("PASS_SOURCE_ACQUISITION_CART_R2")
    assert decision["input_statuses"]["r2a"] == "PASS_KEYED_FULL_WITH_LIMITATIONS"
    assert decision["input_statuses"]["r2b"] == "PASS_R2B_BASE_CITY_PLUS_KEYED_MOBILITY_MERGE_WITH_LIMITATIONS"
    assert all(decision["acceptance"].values())


def test_seed_entity_manifest_has_required_canonical_types():
    manifest = load_json("SEED_ENTITY_MANIFEST.json")
    expected = {
        "community_or_zone_seed",
        "road_segment_seed",
        "building_footprint_seed",
        "place_or_facility_seed",
        "population_cell_seed",
        "weather_context_seed",
        "surface_water_context_seed",
        "energy_donor_profile_seed",
    }
    assert set(manifest["entity_counts"]) == expected
    assert manifest["entity_count"] >= 120
    for entity_type, rows in manifest["seed_entities_by_type"].items():
        assert rows, entity_type
        for row in rows:
            assert row["source_class"]
            assert row["truth_layer"]
            assert row["evidence_refs"] or row["donor_refs"]
            assert row["limitation_refs"]
            assert row["is_real_world_fact"] is False


def test_jsonl_product_feeds_parse_and_carry_source_metadata():
    for name in JSONL_OUTPUTS:
        rows = load_jsonl(name)
        assert rows, name
        for row in rows:
            assert row["source_class"]
            assert row["truth_layer"]
            assert row["evidence_refs"] or row["donor_refs"]
            assert row["limitation_refs"]
            assert row["is_real_world_fact"] is False

    replay = load_jsonl("EVENT_REPLAY_TAPE.jsonl")
    assert len(replay) == 25
    assert all(row["payload"]["local_replay_only"] is True for row in replay)


def test_layer_manifests_and_source_class_ledger():
    for name in ["GOLD_LAYER_MANIFEST.json", "DIRTY_SOURCE_LAYER_MANIFEST.json", "CHALLENGE_LAYER_MANIFEST.json", "SCENARIO_LAYER_MANIFEST.json"]:
        manifest = load_json(name)
        assert manifest["status"] == "PASS"
        assert manifest["record_count"] == len(manifest["records"])
        assert manifest["records"]
        for row in manifest["records"]:
            assert row["source_class"]
            assert row["truth_layer"]
            assert row["evidence_refs"] or row["donor_refs"]
            assert row["limitation_refs"]

    ledger = load_csv("SEED_SOURCE_CLASS_LEDGER.csv")
    assert ledger
    assert any("donor" in row["source_class"] for row in ledger)
    assert any(row["truth_layer"] == "event_replay_synthetic_seed" for row in ledger)


def test_validation_boundary_and_secret_scan_reports_pass():
    validation = load_json("FACTORY_VALIDATION_REPORT.json")
    assert validation["status"] == "PASS"
    assert all(validation["checks"].values())

    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT.json")
    assert boundary["status"] == "PASS"
    assert all(boundary["checks"].values())
    assert boundary["forbidden_text_hits"] == []

    secret_scan = load_json("SECRET_SCAN_REPORT.json")
    assert secret_scan["status"] == "PASS"
    assert secret_scan["pass"] is True
    assert secret_scan["secret_values_tested"] == 4
    assert all(not hits for hits in secret_scan["scans"].values())


def test_hash_manifest_and_package_hygiene():
    hash_manifest = load_json("HASH_MANIFEST.json")
    assert hash_manifest["status"] == "PASS"
    assert hash_manifest["file_count"] == len(REQUIRED_OUTPUTS) - 1
    assert {entry["path"] for entry in hash_manifest["files"]} == set(REQUIRED_OUTPUTS) - {"HASH_MANIFEST.json"}

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
    for name in REQUIRED_OUTPUTS:
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1/{name}" in names
    assert not any(name.lower().endswith(".parquet") for name in names)
    assert not any("/raw/" in name.lower() for name in names)

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE.zip"

REQUIRED_FILES = [
    "R2B_MASTER_DECISION.json",
    "R2B_COMBINED_SOURCE_STATUS_LEDGER.csv",
    "R2B_DOMAIN_FACTORY_FEED_MANIFEST.json",
    "R2B_EXTERNAL_RAW_POINTERS.json",
    "R2B_NORMALIZED_DATASET_INDEX.json",
    "R2B_MOBILITY_DONOR_REPORT.json",
    "R2B_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json",
    "R2B_HTTP_CLIENT_POLICY_REPORT.json",
    "R2B_SECRET_SCAN_REPORT.json",
    "KNOWN_BLOCKERS_R2B.md",
    "CODEX_CLOSEOUT.md",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_r2b_required_outputs_and_master_decision():
    for name in REQUIRED_FILES:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("R2B_MASTER_DECISION.json")
    assert decision["status"] == "PASS_R2B_BASE_CITY_PLUS_KEYED_MOBILITY_MERGE_WITH_LIMITATIONS"
    assert decision["input_statuses"]["r2"] == "PASS_SOURCE_ACQUISITION_CART_R2_P0_FULL_PULL_AND_NORMALIZATION_WITH_LIMITATIONS"
    assert decision["input_statuses"]["r2a"] == "PASS_KEYED_FULL_WITH_LIMITATIONS"
    assert all(decision["acceptance"].values())


def test_r2b_combined_ledger_preserves_r2_and_r2a_statuses():
    rows = load_csv("R2B_COMBINED_SOURCE_STATUS_LEDGER.csv")
    assert len(rows) == 30

    r2_rows = [row for row in rows if row["stage"] == "R2"]
    r2a_rows = [row for row in rows if row["stage"] == "R2A"]
    assert len(r2_rows) == 15
    assert len(r2a_rows) == 15

    assert sum(
        1
        for row in r2a_rows
        if row["source_id"].startswith("lta_")
        and row["source_id"] != "lta_extended_obu_sdk_key"
        and row["status"] == "PASS_SAMPLE_LANDED"
    ) == 8
    assert sum(
        1
        for row in r2a_rows
        if row["source_id"].startswith("tfl_") and row["status"] == "PASS_SAMPLE_LANDED"
    ) == 6
    assert any(
        row["source_id"] == "lta_extended_obu_sdk_key"
        and row["status"] == "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST"
        for row in r2a_rows
    )
    assert any(row["source_id"] == "opsd_time_series" and "donor" in row["source_class"] for row in r2_rows)


def test_r2b_dataset_index_and_domain_boundaries():
    index = load_json("R2B_NORMALIZED_DATASET_INDEX.json")
    assert index["dataset_count"] == 24
    assert index["r2_normalized_dataset_count"] == 9
    assert index["r2a_feed_count"] == 15

    manifest = load_json("R2B_DOMAIN_FACTORY_FEED_MANIFEST.json")
    assert len(manifest["factory_feed_groups"]["base_city_dubai_seed"]) == 7
    assert len(manifest["factory_feed_groups"]["keyed_mobility_donor_context"]) == 15
    assert any("Singapore and London mobility feeds are donor/context feeds" in item for item in manifest["boundaries"])


def test_r2b_mobility_and_http_policy_reports():
    mobility = load_json("R2B_MOBILITY_DONOR_REPORT.json")
    assert mobility["lta"]["pass_count"] == 8
    assert mobility["lta"]["total_count"] == 8
    assert mobility["tfl"]["pass_count"] == 6
    assert mobility["tfl"]["total_count"] == 6
    assert mobility["extended_obu_sdk"]["status"] == "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST"
    assert mobility["no_dispatch_or_control_claim"] is True

    policy = load_json("R2B_HTTP_CLIENT_POLICY_REPORT.json")
    assert policy["required_policy"]["User-Agent"] == "CityBrain/<task-version>"
    assert policy["required_policy"]["Accept"] == "application/json"
    assert "bare urllib" in policy["r2a_observed_lesson"]
    assert "User-Agent" in policy["rule"]


def test_r2b_boundary_audit_replaces_old_tfl_blocker():
    audit = load_json("R2B_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json")
    assert audit["status"] == "PASS"
    assert all(audit["checks"].values())
    assert audit["boundary_replacements"]["old"] == "TFL_KEY_REJECTED_403_NOT_USED_IN_FACTORY_R1"
    assert audit["boundary_replacements"]["new"] == "TFL_CLIENT_HEADER_BLOCKER_RESOLVED_USER_AGENT_REQUIRED"


def test_r2b_secret_scan_and_package_contents():
    scan = load_json("R2B_SECRET_SCAN_REPORT.json")
    assert scan["status"] == "PASS"
    assert scan["pass"] is True
    assert scan["secret_values_tested"] == 4
    assert all(not hits for hits in scan["scans"].values())

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
    for name in REQUIRED_FILES:
        assert f"MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE/{name}" in names
    assert not any("/raw/" in name.lower() or name.lower().endswith(".parquet") for name in names)

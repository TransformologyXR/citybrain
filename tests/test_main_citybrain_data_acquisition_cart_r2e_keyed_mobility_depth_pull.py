from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL"
RAW_ROOT = Path(r"C:\data\citybrain\raw\keyed_mobility_r2e")
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL.zip"

REQUIRED_OUTPUTS = [
    "R2E_MASTER_DECISION.json",
    "SOURCE_STATUS_LEDGER_R2E.csv",
    "DEPTH_PULL_REPORT_R2E.json",
    "DOMAIN_FEED_MANIFEST_R2E.json",
    "RAW_EXTERNAL_CHECKSUM_MANIFEST_R2E.json",
    "SAMPLE_ROW_COUNTS_R2E.csv",
    "NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl",
    "HTTP_CLIENT_POLICY_REPORT_R2E.json",
    "SECRET_SCAN_REPORT_R2E.json",
    "KNOWN_BLOCKERS_RUNTIME_R2E.md",
    "CODEX_CLOSEOUT.md",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_jsonl(name: str) -> list[dict]:
    rows = []
    for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_r2e_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("R2E_MASTER_DECISION.json")
    assert decision["status"] == "PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS"
    assert decision["mode"] == "depth"
    assert decision["source_count"] == 38
    assert decision["pass_count"] == 31
    assert decision["secrets_written"] is False
    assert decision["secret_scan_passed"] is True
    assert "not Dubai truth" in decision["boundary"]


def test_r2e_ledger_counts_and_core_depth_landed():
    rows = load_csv("SOURCE_STATUS_LEDGER_R2E.csv")
    assert len(rows) == 38
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        assert row["secret_redacted"] == "True"
        assert row["donor_context_only"] == "True"
        assert row["not_dubai_truth"] == "True"
        assert "app_key=" not in row["endpoint_template"] or "app_key=REDACTED" in row["endpoint_template"]
    assert counts == {
        "PASS_DEPTH_PAGE_OR_SNAPSHOT_LANDED": 28,
        "PASS_EMPTY_VALID_RESPONSE": 3,
        "FAIL_CLOSED": 5,
        "INFRA_BLOCKED_NOT_AUTH_FAILURE": 1,
        "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST": 1,
    }

    by_id = {row["source_id"]: row for row in rows}
    assert by_id["lta_busstops_full"]["row_count_estimate"] == "5205"
    assert by_id["lta_busroutes_full"]["row_count_estimate"] == "26799"
    assert by_id["lta_roadworks_full"]["row_count_estimate"] == "7656"
    assert by_id["tfl_road_disruptions_all_optional"]["status"].startswith("PASS")
    assert by_id["lta_extended_obu_sdk_key"]["status"] == "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST"


def test_r2e_samples_and_feed_manifest_are_donor_context_only():
    samples = load_jsonl("NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl")
    assert len(samples) == 1180
    for sample in samples[:100]:
        assert sample["donor_context_only"] is True
        assert sample["not_dubai_truth"] is True
        assert sample["source_class"]
        assert sample["limitation_refs"]

    feeds = load_json("DOMAIN_FEED_MANIFEST_R2E.json")
    assert len(feeds) == 38
    assert all(feed["donor_context_only"] is True for feed in feeds)
    assert all(feed["not_dubai_truth"] is True for feed in feeds)
    assert sum(1 for feed in feeds if feed["eligible_for_synthetic_factory_distribution_donor"] is True) == 31


def test_r2e_raw_manifest_and_http_policy():
    raw_manifest = load_json("RAW_EXTERNAL_CHECKSUM_MANIFEST_R2E.json")
    assert len(raw_manifest) == 110
    for entry in raw_manifest:
        path = Path(entry["path"])
        assert path.exists()
        assert str(path).startswith(str(RAW_ROOT))
        assert entry["bytes"] > 0
        assert len(entry["sha256"]) == 64

    policy = load_json("HTTP_CLIENT_POLICY_REPORT_R2E.json")
    assert policy["required_headers"]["User-Agent"] == "CityBrain-R2E/1.0"
    assert policy["required_headers"]["Accept"] == "application/json"
    assert "200/201" in policy["success_payload_policy"]
    assert "Do not persist failed response bodies" in policy["failure_body_policy"]


def test_r2e_secret_scan_and_package_hygiene():
    scan = load_json("SECRET_SCAN_REPORT_R2E.json")
    assert scan["passed"] is True
    assert scan["secret_count"] == 4
    assert scan["findings"] == []
    assert any("packages" in root for root in scan["scanned_roots"])
    assert any(str(RAW_ROOT) in root for root in scan["scanned_roots"])

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
    for name in REQUIRED_OUTPUTS:
        assert f"MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL/{name}" in names
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith(".parquet") for name in names)


def test_r2e_known_limitations_are_fail_closed_not_auth_leaks():
    blockers = (OUTPUT_ROOT / "KNOWN_BLOCKERS_RUNTIME_R2E.md").read_text(encoding="utf-8")
    assert "lta_bus_arrival_sample_optional" in blockers
    assert "tfl_stoppoint_by_mode_national-rail" in blockers
    assert "tfl_accident_stats_recent_optional_2025" in blockers
    assert "app_key=" not in blockers

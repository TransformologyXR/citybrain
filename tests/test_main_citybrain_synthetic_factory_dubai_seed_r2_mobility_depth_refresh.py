from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH.zip"

REQUIRED_OUTPUTS = [
    "SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_DECISION.json",
    "R2_INPUT_READONLY_LINEAGE.json",
    "MOBILITY_DEPTH_DONOR_SUMMARY_R2.json",
    "MOBILITY_DISTRIBUTION_PROFILE_R2.json",
    "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl",
    "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl",
    "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl",
    "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl",
    "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl",
    "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl",
    "FACTORY_VALIDATION_REPORT_R2.json",
    "BOUNDARY_AND_NO_ACTION_AUDIT_R2.json",
    "SECRET_SCAN_REPORT_R2.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

JSONL_OUTPUTS = [
    "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl",
    "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl",
    "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl",
    "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl",
    "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl",
    "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_jsonl(name: str) -> list[dict]:
    rows = []
    for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def assert_source_metadata(row: dict) -> None:
    assert row["source_class"]
    assert row["truth_layer"]
    assert "donor_refs" in row
    assert "evidence_refs" in row
    assert row["donor_refs"] or row["evidence_refs"]
    assert row["limitation_refs"]
    assert row["is_real_world_fact"] is False


def test_seed_r2_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS"
    assert decision["input_statuses"]["seed_r1"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS"
    assert decision["input_statuses"]["r2e"] == "PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS"
    assert decision["counts"] == {
        "event_replay_rows": 30,
        "watch_rows": 6,
        "ask_rows": 6,
        "check_rows": 6,
        "brief_rows": 6,
        "spatial_rows": 6,
        "r2e_normalized_sample_rows_consumed": 1180,
        "r2e_status_rows": 38,
    }
    assert all(decision["acceptance"].values())


def test_seed_r2_lineage_and_donor_summary_are_readonly_donor_context():
    lineage = load_json("R2_INPUT_READONLY_LINEAGE.json")
    assert lineage["seed_r1_read_only"] is True
    assert lineage["r2e_read_only"] is True
    assert lineage["inputs_not_mutated_by_design"] is True

    summary = load_json("MOBILITY_DEPTH_DONOR_SUMMARY_R2.json")
    assert summary["r2e_status"] == "PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS"
    assert summary["r2e_source_count"] == 38
    assert summary["r2e_passing_feed_count"] == 31
    assert summary["r2e_raw_success_payload_files"] == 110
    assert summary["r2e_normalized_sample_rows"] == 1180
    assert summary["r2e_secret_scan_status"] == "PASS"
    assert summary["donor_context_only"] is True
    assert summary["not_dubai_truth"] is True

    profile = load_json("MOBILITY_DISTRIBUTION_PROFILE_R2.json")
    assert profile["donor_context_only"] is True
    assert profile["not_dubai_truth"] is True
    assert profile["sample_row_count"] == 1180
    assert profile["passing_feed_count"] == 31


def test_seed_r2_jsonl_records_parse_and_carry_required_metadata():
    expected_counts = {
        "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl": 30,
        "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl": 6,
        "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl": 6,
        "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl": 6,
        "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl": 6,
        "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl": 6,
    }
    for name, count in expected_counts.items():
        rows = load_jsonl(name)
        assert len(rows) == count
        for row in rows:
            assert_source_metadata(row)

    replay_rows = load_jsonl("EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl")
    assert all(row["payload"]["local_replay_only"] is True for row in replay_rows)
    assert all(row["payload"]["live_monitoring"] is False for row in replay_rows)
    assert all(row["payload"]["not_dubai_truth"] is True for row in replay_rows)


def test_seed_r2_check_fixtures_reject_live_dubai_action_claims():
    rows = load_jsonl("CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl")
    for row in rows:
        payload = row["payload"]
        assert payload["expected_result"] == "reject_as_not_claimable"
        assert "live Dubai" in payload["claim_text"]
        assert "dispatch" in payload["claim_text"] or "route a response" in payload["claim_text"]
        assert "not a live Dubai" in payload["required_safe_rewrite"]


def test_seed_r2_validation_boundary_and_secret_reports_pass():
    validation = load_json("FACTORY_VALIDATION_REPORT_R2.json")
    assert validation["status"] == "PASS"
    assert validation["record_validation_errors"] == []
    assert all(validation["checks"].values())

    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT_R2.json")
    assert boundary["status"] == "PASS"
    for key, value in boundary.items():
        if key.startswith("no_") or key.endswith("_read_only"):
            assert value is True, key

    secret_scan = load_json("SECRET_SCAN_REPORT_R2.json")
    assert secret_scan["status"] == "PASS"
    assert secret_scan["passed"] is True
    assert secret_scan["secret_values_tested"] == 4
    assert secret_scan["findings"] == []
    assert all(not hits for hits in secret_scan["scans"].values())


def test_seed_r2_hash_manifest_package_hygiene_and_redaction():
    hash_manifest = load_json("HASH_MANIFEST.json")
    assert hash_manifest["status"] == "PASS"
    assert hash_manifest["file_count"] == len(REQUIRED_OUTPUTS) - 1
    assert {entry["path"] for entry in hash_manifest["entries"]} == set(REQUIRED_OUTPUTS) - {"HASH_MANIFEST.json"}

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
        payload_text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.endswith((".json", ".jsonl", ".csv", ".md", ".txt"))
        )
    for name in REQUIRED_OUTPUTS:
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH/{name}" in names
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith(".parquet") for name in names)
    assert not re.search(r"app_key=(?!REDACTED)[A-Za-z0-9_\-]{8,}", payload_text)

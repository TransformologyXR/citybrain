from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN"

REQUIRED_FILES = [
    "R2A_MASTER_DECISION.json",
    "SOURCE_STATUS_LEDGER_R2A.csv",
    "HARVEST_REPORT_R2A.json",
    "DOMAIN_FEED_MANIFEST_R2A.json",
    "SAMPLE_ROW_COUNTS_R2A.csv",
    "RAW_EXTERNAL_CHECKSUM_MANIFEST_R2A.json",
    "KNOWN_BLOCKERS_RUNTIME.md",
    "CODEX_CLOSEOUT.md",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))


def load_csv(name: str):
    with (OUTPUT_ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_required_r2a_outputs_exist_and_parse():
    for name in REQUIRED_FILES:
        path = OUTPUT_ROOT / name
        assert path.exists(), name
        if path.suffix == ".json":
            assert load_json(name) is not None


def test_full_run_decision_and_harvest_counts_are_consistent():
    decision = load_json("R2A_MASTER_DECISION.json")
    report = load_json("HARVEST_REPORT_R2A.json")
    assert decision["status"] == "PASS_KEYED_FULL_WITH_LIMITATIONS"
    assert report["mode"] == "full"
    assert report["secrets_written"] is False
    assert report["source_count"] == 15
    assert report["status_counts"] == {
        "PASS_SAMPLE_LANDED": 14,
        "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST": 1,
    }
    assert all(report["credential_presence"].values())


def test_lta_and_tfl_pass_and_sdk_is_not_used_for_rest():
    rows = {row["source_id"]: row for row in load_csv("SOURCE_STATUS_LEDGER_R2A.csv")}
    lta_sources = [source_id for source_id in rows if source_id.startswith("lta_") and source_id != "lta_extended_obu_sdk_key"]
    tfl_sources = [source_id for source_id in rows if source_id.startswith("tfl_")]
    assert len(lta_sources) == 8
    assert len(tfl_sources) == 6
    for source_id in lta_sources + tfl_sources:
        assert rows[source_id]["status"] == "PASS_SAMPLE_LANDED"
        assert rows[source_id]["auth_status"] == "KEY_ACCEPTED"
        assert rows[source_id]["sample_sha256"]
    for source_id in tfl_sources:
        assert "REDACTED" in rows[source_id]["endpoint_template"]
    assert rows["lta_extended_obu_sdk_key"]["status"] == "KEY_PRESENT_NOT_USED_FOR_STANDARD_REST"


def test_raw_payloads_are_external_and_hashed():
    manifest = load_json("RAW_EXTERNAL_CHECKSUM_MANIFEST_R2A.json")
    assert manifest
    for row in manifest:
        path = Path(row["path"])
        assert path.exists(), row
        assert str(path).startswith("C:\\data\\citybrain\\raw\\keyed_mobility_r2a")
        assert int(row["bytes"]) > 0
        assert row["sha256"]


def test_domain_manifest_has_transport_context_boundary_only():
    feeds = load_json("DOMAIN_FEED_MANIFEST_R2A.json")
    assert len(feeds) == 15
    classes = {feed["source_class"] for feed in feeds}
    assert "live_or_current_transport_context" in classes
    assert "blocked_or_unvalidated" in classes
    assert all("dispatch" not in json.dumps(feed).lower() for feed in feeds)

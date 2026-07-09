from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_trackb_maturity_brief_governance_r1.py"

spec = importlib.util.spec_from_file_location("trackb_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_decision_exists_and_has_with_limitations():
    runner.build_outputs()
    decision = load_json(runner.OUTPUT_ROOT / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json")
    assert decision["status"] == runner.FINAL_STATUS
    assert decision["status"].endswith("_WITH_LIMITATIONS")


def test_dashboard_preserves_nine_scorecard_categories():
    dashboard = load_json(runner.OUTPUT_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json")
    assert {card["scorecard_id"] for card in dashboard["scorecards"]} == set(runner.REQUIRED_SCORECARDS)
    assert dashboard["top_gap_refs"]


def test_three_brief_variants_exist_and_pass_parity_checks():
    for name in [
        "BRIEF_V3_OPERATOR_VARIANT.md",
        "BRIEF_V3_EXECUTIVE_VARIANT.md",
        "BRIEF_V3_TECHNICAL_VARIANT.md",
    ]:
        assert (runner.OUTPUT_ROOT / name).exists()
    parity = load_json(runner.OUTPUT_ROOT / "BRIEF_V3_VARIANT_PARITY_REPORT.json")
    assert parity["variant_count"] == 3
    assert parity["all_variants_share_evidence_signature"] is True
    assert parity["claim_authority_changed"] is False


def test_governance_audit_emits_required_guard_files():
    for name in [
        "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.json",
        "FORBIDDEN_CLAIM_SCAN_RESULTS.json",
        "BOUNDARY_LANGUAGE_FINDINGS.json",
        "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
        "NO_LIVE_INGESTION_CLAIM_GUARD.json",
        "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json",
        "GOVERNANCE_REMEDIATION_SUGGESTIONS.json",
    ]:
        assert (runner.OUTPUT_ROOT / name).exists()
    assert load_json(runner.OUTPUT_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json")["status"] == "PASS"
    assert load_json(runner.OUTPUT_ROOT / "NO_LIVE_INGESTION_CLAIM_GUARD.json")["status"] == "PASS"
    assert load_json(runner.OUTPUT_ROOT / "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json")["status"] == "PASS"


def test_no_forbidden_capabilities_are_created():
    guard = load_json(runner.OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert guard["status"] == "PASS"
    assert guard["forbidden_capabilities_created"] == []
    assert all(value is False for value in guard["checks"].values())


def test_hash_manifest_covers_packaged_outputs():
    manifest = load_json(runner.OUTPUT_ROOT / "HASH_MANIFEST.json")
    paths = {entry["path"] for entry in manifest["entries"]}
    for name in runner.OUTPUT_FILES:
        if name != "HASH_MANIFEST.json":
            assert f"outputs/main_citybrain_epoch4_trackb_maturity_brief_governance_r1/{name}" in paths
    assert runner.validate_outputs() == []

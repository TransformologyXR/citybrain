from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_deep_data_estate_audit_r1.py"

spec = importlib.util.spec_from_file_location("deep_data_estate_audit_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_outputs_and_decision_status_with_limitations():
    runner.build_outputs()
    decision = load_json(runner.OUTPUT_ROOT / "DATA_ESTATE_AUDIT_DECISION.json")
    assert decision["status"] == runner.FINAL_STATUS
    assert decision["status"].endswith("_WITH_LIMITATIONS")
    assert decision["read_only"] is True


def test_required_outputs_tables_and_json_parse():
    for name in runner.REQUIRED_JSON_OUTPUTS:
        payload = load_json(runner.OUTPUT_ROOT / name)
        assert payload
    for name in runner.REQUIRED_MD_OUTPUTS + runner.REQUIRED_TABLES:
        path = runner.OUTPUT_ROOT / name
        assert path.exists()
        assert path.stat().st_size > 0


def test_no_forbidden_capabilities_and_mutation_flags_are_false():
    decision = load_json(runner.OUTPUT_ROOT / "DATA_ESTATE_AUDIT_DECISION.json")
    guard = load_json(runner.OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert guard["status"] == "PASS"
    assert guard["forbidden_capabilities_created"] == []
    assert all(value is False for value in guard["checks"].values())
    for flag in [
        "source_truth_mutation",
        "training_rows_created",
        "operator_fuel_created",
        "forecast_packet_created",
        "product_forecast_surface_created",
        "live_ingestion_claim_created",
        "official_case_ticket_action_created",
        "dispatch_control_enforcement_created",
    ]:
        assert decision[flag] is False


def test_inventory_and_coverage_are_nonempty():
    inventory = load_json(runner.OUTPUT_ROOT / "DATA_ROOT_INVENTORY.json")
    coverage = load_json(runner.OUTPUT_ROOT / "CITY_DOMAIN_COVERAGE_MATRIX.json")
    source_crosswalk = load_json(runner.OUTPUT_ROOT / "SOURCE_REGISTRY_CROSSWALK.json")
    assert inventory["scan_roots"]
    assert inventory["existing_root_count"] >= 1
    assert coverage["matrix"]
    assert source_crosswalk["source_count"] >= 1


def test_eval_founder_and_synthetic_counts_are_evidence_backed():
    eval_audit = load_json(runner.OUTPUT_ROOT / "PRODUCT_LOOP_EVAL_COVERAGE_AUDIT.json")
    founder = load_json(runner.OUTPUT_ROOT / "FOUNDER_PROBE_REPRESENTATIVENESS_CROSSWALK.json")
    synthetic = load_json(runner.OUTPUT_ROOT / "SYNTHETIC_DATA_FACTORY_AUDIT.json")
    assert eval_audit["eval_case_count"] == 48
    assert eval_audit["separate_challenge_negative_suite_count"] == 32
    assert founder["founder_card_count"] == 16
    assert synthetic["comparison_count"] == len(runner.REFERENCE_COUNTS)
    assert synthetic["matched_count"] >= 8


def test_hash_manifest_verifies_and_validate_only_contract_passes():
    manifest = load_json(runner.OUTPUT_ROOT / "HASH_MANIFEST.json")
    assert manifest["status"] == "PASS"
    assert manifest["entries"]
    for entry in manifest["entries"]:
        path = runner.ROOT / entry["path"]
        assert path.exists()
        assert runner.sha256_file(path) == entry["sha256"]
    assert runner.validate_outputs() == []


def test_next_move_is_singular_and_allowed():
    recommendation = load_json(runner.OUTPUT_ROOT / "NEXT_MOVE_RECOMMENDATION.json")
    allowed = {
        "EXPAND_EVAL_CORPUS_FIRST",
        "RUN_FOUNDER_DIAGNOSTIC_REVIEW",
        "FIX_REVIEW_PACK_QUALITY_FIRST",
        "DEEPEN_DATA_MATURITY_REMEDIATION",
        "DEEPEN_EVENT_FABRIC_OR_SIMULATION",
        "READY_FOR_INTERNAL_PRODUCT_SNAPSHOT",
    }
    assert recommendation["top_recommendation"] in allowed
    assert recommendation["top_recommendation"] == "FIX_REVIEW_PACK_QUALITY_FIRST"

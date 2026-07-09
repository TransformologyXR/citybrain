from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_pre_e4_three_package_repair_chain.py"

spec = importlib.util.spec_from_file_location("pre_e4_chain", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    missing = [runner.rel(path) for path in runner.required_output_paths() if not path.exists()]
    assert missing == []


def test_backlog_ledger_dedupe_counts_are_raw_signal_safe():
    dedupe = load_json(runner.OUT["master"] / "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json")
    raw_ids = [item_id for group in dedupe["artifact_groups"] for item_id in group["raw_item_ids"]]
    assert dedupe["raw_ledger_item_count"] == 21
    assert dedupe["canonical_artifact_group_count"] == 12
    assert len(raw_ids) == 21
    assert len(set(raw_ids)) == 21
    assert dedupe["no_duplicate_done_inflation"] is True
    assert dedupe["completion_count_basis"] == "canonical_artifact_groups"


def test_event_fabric_contracts_and_replay_are_local_only():
    contract_files = sorted(runner.CONTRACTS["event"].glob("*.schema.json"))
    assert len(contract_files) == 6
    replay = load_json(runner.OUT["event"] / "EVENT_REPLAY_REPORT.json")
    current = load_json(runner.OUT["event"] / "EVENT_CURRENT_STATE.json")
    guard = load_json(runner.OUT["event"] / "NO_LIVE_INGESTION_CLAIM_GUARD.json")
    assert replay["deterministic"] is True
    assert current["counts"]["unresolved"] == 1
    assert current["counts"]["quarantined"] == 1
    assert guard["forbidden_capabilities_created"] == []
    assert guard["official_action_created"] is False


def test_simulation_catalog_supersedes_master_pointer_without_forecast():
    scenarios = load_json(runner.OUT["simulation"] / "SIMULATION_SCENARIO_CATALOG_R1.json")
    catalog = load_json(runner.OUT["simulation"] / "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json")
    reconciliation = load_json(runner.OUT["simulation"] / "SIMULATION_MASTER_POINTER_RECONCILIATION_R1.json")
    forecast_guard = load_json(runner.OUT["simulation"] / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json")
    assert scenarios["scenario_count"] >= 4
    assert catalog["supersedes_master_pointer"] is True
    assert catalog["no_fake_transition_history_generated"] is True
    assert reconciliation["relationship"] == "supersedes_provisional_pointer"
    assert forecast_guard["product_forecast_surface_created"] is False


def test_three_package_reverify_decision_and_guards():
    decision = load_json(runner.OUT["reverify"] / "THREE_PACKAGE_SEQUENCE_DECISION.json")
    source_audit = load_json(runner.OUT["reverify"] / "THREE_PACKAGE_SOURCE_REF_AUDIT.json")
    dedupe_reverify = load_json(runner.OUT["reverify"] / "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json")
    guard = load_json(runner.OUT["reverify"] / "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert decision["status"] == "PASS_MAIN_CITYBRAIN_PRE_E4_THREE_PACKAGE_REVERIFY_R1_WITH_LIMITATIONS"
    assert decision["parallel_execution_used"] is False
    assert source_audit["all_required_present_and_hash_stable"] is True
    assert dedupe_reverify["raw_ledger_item_count"] == 21
    assert dedupe_reverify["canonical_artifact_group_count"] == 12
    assert dedupe_reverify["no_duplicate_done_inflation"] is True
    assert guard["forbidden_capabilities_created"] == []


def test_hash_manifests_verify():
    for manifest_path in [
        runner.OUT["master"] / "HASH_MANIFEST.json",
        runner.OUT["event"] / "HASH_MANIFEST.json",
        runner.OUT["simulation"] / "HASH_MANIFEST.json",
        runner.OUT["reverify"] / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(manifest_path) == []


def test_runner_validation_is_clean():
    assert runner.validate_all() == []

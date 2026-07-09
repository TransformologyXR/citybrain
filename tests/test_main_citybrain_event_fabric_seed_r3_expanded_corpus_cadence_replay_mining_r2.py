from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_event_fabric_seed_r3_expanded_corpus_cadence_replay_mining_r2.py"

spec = importlib.util.spec_from_file_location("expanded_cadence_r2", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json").exists():
        runner.build(runner.DEFAULT_EXPANDED_CORPUS_ROOT, runner.DEFAULT_OUT)


def test_required_outputs_exist():
    runner.build(runner.DEFAULT_EXPANDED_CORPUS_ROOT, runner.DEFAULT_OUT)
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_input_integrity_counts():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json")
    assert decision["status"] == runner.STATUS
    assert decision["input_event_count"] == 80
    assert decision["family_count"] == 4
    assert set(decision["canonical_loop_family_ids"]) == set(runner.FAMILIES)
    assert all(count == 20 for count in decision["events_per_family"].values())
    assert decision["resolved_count"] == 40
    assert decision["unresolved_review_count"] == 20
    assert decision["quarantine_expected_count"] == 20
    assert decision["duplicate_candidate_ambiguity_count"] >= 8


def test_all_cadence_modes_have_identical_hash_and_partition():
    ensure_outputs()
    hashes = load_json(runner.DEFAULT_OUT / "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json")
    assert [row["mode"] for row in hashes["modes"]] == runner.MODES
    assert hashes["identical_final_state_hash"] is True
    assert hashes["identical_resolved_unresolved_quarantine_partition"] is True
    assert len(hashes["final_state_hash_values"]) == 1
    assert len(hashes["partition_hash_values"]) == 1
    assert runner.read_jsonl(runner.DEFAULT_OUT / "EXPANDED_CORPUS_CADENCE_DISAGREEMENT_LEDGER.jsonl") == []


def test_replay_ledgers_and_queue_mining_label():
    ensure_outputs()
    materialized = runner.read_jsonl(runner.DEFAULT_OUT / "EXPANDED_CORPUS_REPLAY_MATERIALIZED_STATE.jsonl")
    outcome = runner.read_jsonl(runner.DEFAULT_OUT / "EXPANDED_CORPUS_REPLAY_OUTCOME_LEDGER.jsonl")
    queue = load_json(runner.DEFAULT_OUT / "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json")
    assert len(materialized) == 80
    assert len(outcome) == 80
    assert queue["classification"] == runner.QUEUE_MINING_LABEL
    assert queue["not_real_world_resolution_quality_signal"] is True
    assert set(queue["family_reports"]) == set(runner.FAMILIES)


def test_reason_and_canonical_replay_validation():
    ensure_outputs()
    reasons = load_json(runner.DEFAULT_OUT / "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED.json")
    canonical = load_json(runner.DEFAULT_OUT / "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json")
    assert reasons["matches_input_distribution"] is True
    assert canonical["matches_input_counts"] is True
    assert canonical["canonical_resolved_event_count"] == 20
    assert canonical["r3_local_or_synthetic_admitted_event_count"] == 60


def test_guards_manifest_and_validate():
    ensure_outputs()
    d5d6 = load_json(runner.DEFAULT_OUT / "NO_DIRECT_D5D6_BYPASS_GUARD.json")
    fixture = load_json(runner.DEFAULT_OUT / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert d5d6["direct_d5_d6_bypass"] is False
    assert fixture["standalone_watch_ask_check_brief_spatial_fixture_surface_created"] is False
    assert boundary["source_truth_mutated"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["operator_fuel_created"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []

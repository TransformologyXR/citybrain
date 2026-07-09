from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_event_fabric_seed_r3_cadence_replay_quarantine_mining_r1.py"

spec = importlib.util.spec_from_file_location("seed_r3_cadence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "SEED_R3_CADENCE_REPLAY_DECISION.json").exists():
        runner.build(runner.DEFAULT_ADAPTER_ROOT, runner.DEFAULT_OUT)


def test_required_outputs_exist():
    runner.build(runner.DEFAULT_ADAPTER_ROOT, runner.DEFAULT_OUT)
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_replay_counts_and_canonical_families():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "SEED_R3_CADENCE_REPLAY_DECISION.json")
    normalized = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_CONVERGED_STREAM_NORMALIZED.jsonl")
    assert decision["input_event_count"] == 16
    assert decision["resolved_count"] == 8
    assert decision["unresolved_review_count"] == 4
    assert decision["quarantine_expected_count"] == 4
    assert set(decision["canonical_loop_family_ids"]) == set(runner.FAMILIES)
    assert {row["canonical_loop_family_id"] for row in normalized} == set(runner.FAMILIES)


def test_all_cadence_modes_have_identical_final_state_hash():
    ensure_outputs()
    runs = [
        load_json(runner.DEFAULT_OUT / "SEED_R3_REPLAY_RUN_BATCH.json"),
        load_json(runner.DEFAULT_OUT / "SEED_R3_REPLAY_RUN_10X.json"),
        load_json(runner.DEFAULT_OUT / "SEED_R3_REPLAY_RUN_60X.json"),
        load_json(runner.DEFAULT_OUT / "SEED_R3_REPLAY_RUN_WALL_CLOCK_SIMULATED.json"),
    ]
    hashes = {run["final_state_hash"] for run in runs}
    assert len(hashes) == 1
    consistency = load_json(runner.DEFAULT_OUT / "SEED_R3_CADENCE_CONSISTENCY_REPORT.json")
    assert consistency["identical_final_state_hash"] is True
    assert consistency["cadence_consistency_status"] == "PASS"


def test_unresolved_quarantine_and_queue_mining_depth_label():
    ensure_outputs()
    unresolved = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_UNRESOLVED_QUEUE.jsonl")
    quarantine = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_QUARANTINE_QUEUE.jsonl")
    mining = load_json(runner.DEFAULT_OUT / "SEED_R3_QUEUE_MINING_REPORT.json")
    assert len(unresolved) == 4
    assert len(quarantine) == 4
    assert mining["classification"] == "pipeline_proof_depth_1"
    assert mining["not_resolution_quality_signal"] is True
    assert mining["requires_adapter_corpus_expansion_before_story_arc"] is True
    assert len(mining["family_reports"]) == 4


def test_no_bypass_no_standalone_fixture_and_boundary_guards():
    ensure_outputs()
    d5d6 = load_json(runner.DEFAULT_OUT / "NO_DIRECT_D5D6_BYPASS_GUARD.json")
    fixture = load_json(runner.DEFAULT_OUT / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert d5d6["direct_d5_d6_bypass"] is False
    assert fixture["standalone_watch_ask_check_brief_spatial_fixture_surface_created"] is False
    assert boundary["official_workflow_case_action_created"] is False
    assert boundary["source_truth_mutated"] is False


def test_manifest_and_validate_pass():
    ensure_outputs()
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []

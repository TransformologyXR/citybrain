from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_seed_r3_adapter_corpus_expansion_r1.py"

spec = importlib.util.spec_from_file_location("seed_r3_expansion", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json").exists():
        runner.build(runner.DEFAULT_ADAPTER_ROOT, runner.DEFAULT_CADENCE_ROOT, runner.DEFAULT_OUT)


def test_required_outputs_exist():
    runner.build(runner.DEFAULT_ADAPTER_ROOT, runner.DEFAULT_CADENCE_ROOT, runner.DEFAULT_OUT)
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_expanded_feed_preserves_four_families_and_target_counts():
    ensure_outputs()
    events = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")
    counts = Counter(event["canonical_loop_family_id"] for event in events)
    assert len(events) == 80
    assert set(counts) == set(runner.FAMILIES)
    assert all(counts[family] == 20 for family in runner.FAMILIES)
    assert all(event["schema_version"] == "event_fabric_source_adapter.v1" for event in events)


def test_resolution_floors_and_queues():
    ensure_outputs()
    counts = load_json(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json")
    unresolved = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl")
    quarantine = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl")
    assert unresolved
    assert quarantine
    for row in counts["rows"]:
        assert row["event_count"] == 20
        assert row["resolved_count"] >= 8
        assert row["unresolved_review_count"] >= 3
        assert row["quarantine_expected_count"] >= 3
        assert row["distinct_reason_class_count"] >= 2


def test_canonical_resolution_and_duplicate_ambiguity_present():
    ensure_outputs()
    canonical = load_json(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json")
    duplicates = runner.read_jsonl(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl")
    assert canonical["canonical_resolved_event_count"] > 0
    assert canonical["r3_local_or_synthetic_admitted_event_count"] > 0
    assert duplicates
    assert all(row["reason_class"] == "duplicate_candidate_ambiguity" for row in duplicates)


def test_readiness_and_story_arc_gate():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json")
    corpus = load_json(runner.DEFAULT_OUT / "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE.json")
    story = load_json(runner.DEFAULT_OUT / "SEED_R3_STORY_ARC_READINESS_GATE.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["story_arc_readiness"] == "story_arc_ready_with_limitations"
    assert corpus["status"] == "PASS_WITH_LIMITATIONS"
    assert corpus["family_gate_pass"] is True
    assert story["story_arc_ready"] is True
    assert story["story_arc_readiness"] == "story_arc_ready_with_limitations"


def test_guards_and_manifest_validate():
    ensure_outputs()
    fixture = load_json(runner.DEFAULT_OUT / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json")
    d5d6 = load_json(runner.DEFAULT_OUT / "NO_DIRECT_D5D6_BYPASS_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert fixture["standalone_watch_ask_check_brief_spatial_fixture_surface_created"] is False
    assert d5d6["direct_d5_d6_bypass"] is False
    assert boundary["source_truth_mutated"] is False
    assert boundary["live_ingestion_created"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["official_workflow_case_action_created"] is False
    assert boundary["training_rows_created"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []

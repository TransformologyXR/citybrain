from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1.py"

spec = importlib.util.spec_from_file_location("sprint0_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_required_outputs_and_contracts_exist():
    missing = [
        runner.rel(path)
        for path in [runner.OUTPUT_ROOT / name for name in runner.REQUIRED_OUTPUTS] + runner.REQUIRED_CONTRACTS
        if not path.exists()
    ]
    assert missing == []


def test_prior_repair_chain_intake_and_source_refs_pass():
    source_audit = load_json(runner.OUTPUT_ROOT / "SPRINT0_SOURCE_REF_AUDIT.json")
    intake = load_json(runner.OUTPUT_ROOT / "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE.json")
    assert source_audit["status"] == "PASS"
    assert source_audit["missing_files"] == []
    assert intake["status"] == "PASS"
    assert intake["event_fabric_r1_contract_count"] == 6
    assert intake["simulation_r1_contract_count"] == 7
    assert intake["parallel_execution_used"] is False


def test_cer_engine_has_confidence_provenance_conflicts_and_review_state():
    cer_run = load_json(runner.OUTPUT_ROOT / "CER_ENTITY_RESOLUTION_RUN_R1.json")
    conflict_report = load_json(runner.OUTPUT_ROOT / "CER_CONFLICT_REPORT_R1.json")
    review_queue = load_jsonl(runner.OUTPUT_ROOT / "CER_REVIEW_QUEUE_R1.jsonl")
    assert cer_run["official_truth_mutated"] is False
    assert cer_run["canonical_truth_mutated"] is False
    assert len(cer_run["canonical_entities"]) >= 2
    assert len(cer_run["source_entity_links"]) >= 5
    for entity in cer_run["canonical_entities"]:
        assert entity["confidence"] >= 0
        assert entity["provenance_refs"]
        assert entity["review_state"] in {"candidate_reviewed", "review_required", "conflicted", "verified_fixture"}
    assert conflict_report["conflict_count"] >= 1
    assert conflict_report["unresolved_conflicts_promoted_to_truth"] is False
    assert any(item["review_state"] == "review_required" for item in review_queue)


def test_seg_bridge_uses_cer_ids_and_rejects_raw_bypass():
    edges = load_jsonl(runner.OUTPUT_ROOT / "SEG_EDGE_ASSERTIONS_R1.jsonl")
    guard = load_json(runner.OUTPUT_ROOT / "SEG_NO_RAW_ID_BYPASS_GUARD.json")
    report = load_json(runner.OUTPUT_ROOT / "SEG_V2_CER_BRIDGE_REPORT.json")
    assert report["all_edges_use_cer_backed_ids"] is True
    assert report["raw_id_bypass_rejected"] is True
    for edge in edges:
        assert edge["subject_cer_entity_id"].startswith("cer:")
        assert edge["object_cer_entity_id"].startswith("cer:")
        assert edge["temporal_validity"]
        assert "edge_confidence" in edge
        assert edge["evidence_refs"]
        assert edge["review_state"]
    assert all(item["rejected"] for item in guard["raw_id_bypass_attempts"])


def test_check_v1_rule_coverage_and_downgrades():
    reports = load_jsonl(runner.OUTPUT_ROOT / "CHECK_V1_REPORTS.jsonl")
    coverage = load_json(runner.OUTPUT_ROOT / "CHECK_V1_RULE_COVERAGE_MATRIX.json")
    statuses = {report["claimability_status"] for report in reports}
    assert coverage["all_required_rules_covered"] is True
    for rule_name, row in coverage["rules"].items():
        assert row["covered"], rule_name
    assert "claimable_with_limitations" in statuses
    assert "blocked_contradiction" in statuses
    assert "blocked_stale" in statuses
    assert "blocked_insufficient_source_depth" in statuses
    assert "downgraded_proximity_only" in statuses
    assert "downgraded_candidate_only" in statuses
    assert "blocked_raw_id_bypass" in statuses
    for report in reports:
        assert report["canonical_entity_refs"]
        assert report["authority_boundary"] == "review_only_no_action"


def test_integrated_trust_gate_and_negative_fixtures():
    integrated = load_json(runner.OUTPUT_ROOT / "SPRINT0_INTEGRATED_TRUST_GATE_REPORT.json")
    negatives = load_json(runner.OUTPUT_ROOT / "SPRINT0_NEGATIVE_FIXTURE_RESULTS.json")
    assert integrated["status"] == "PASS_WITH_LIMITATIONS"
    assert integrated["integrated_gate"] == "source_record_to_cer_to_seg_to_check"
    assert integrated["positive_pipeline"]["source_record"]
    assert integrated["positive_pipeline"]["cer_entity"].startswith("cer:")
    assert integrated["positive_pipeline"]["seg_context"].startswith("seg_edge:")
    assert integrated["positive_pipeline"]["check_report"].startswith("check_v1:")
    assert negatives["all_negative_fixtures_passed"] is True
    assert negatives["negative_fixture_count"] >= 6


def test_final_decision_and_hash_manifest_verify():
    decision = load_json(runner.OUTPUT_ROOT / "SPRINT0_DECISION.json")
    assert decision["status"] == runner.FINAL_STATUS
    assert decision["forbidden_capabilities_created"] == []
    assert decision["parallel_execution_used"] is False
    assert decision["hash_manifest_verified"] is True
    assert runner.verify_hash_manifest() == []


def test_runner_validation_is_clean():
    assert runner.validate_outputs() == []

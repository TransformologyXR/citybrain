from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_hidden_data_scout_master_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_hidden_data_scout_master_r1"
EXPECTED_STATUS = "PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = {
    "E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json",
    "E3_ARTIFACT_ROOT_INVENTORY.json",
    "E3_HIDDEN_TRANSITION_TARGET_CATALOG.json",
    "E3_HIDDEN_TRANSITION_TARGET_SCOUT_REPORT.json",
    "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json",
    "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json",
    "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json",
    "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT.json",
    "E3_GLOBAL_HIDDEN_DATA_BACKLOG.json",
    "E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA.json",
    "E3_HIDDEN_DATA_SCOUT_NO_MODEL_GUARD_REPORT.json",
    "E3_HIDDEN_DATA_SCOUT_LIMITATIONS.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}

REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "candidate_family",
    "scout_lane",
    "source_roots",
    "source_refs",
    "source_class",
    "city",
    "domain_pack",
    "temporal_fields_present",
    "lineage_strength",
    "labelability_or_usefulness_rating",
    "promotion_status",
    "recommended_follow_on",
    "limitations",
}

TRACK0_DIMENSIONS = {
    "Watch ranking descriptive signals",
    "domain-pack usefulness",
    "simulation/backtest inputs",
    "synthetic/gold/dirty/challenge/scenario gaps",
    "operator/fuel-program health",
    "source-refresh longitudinal gaps",
    "federation/cross-city comparable artifacts",
    "data quality/maturity diagnostics",
    "spatial/Omniverse traces",
    "workflow/review-state history",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def all_candidates() -> list[dict]:
    reports = [
        load_json(OUTPUT_ROOT / "E3_HIDDEN_TRANSITION_TARGET_CATALOG.json")["candidates"],
        load_json(OUTPUT_ROOT / "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json")["candidates"],
        load_json(OUTPUT_ROOT / "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json")["candidates"],
        load_json(OUTPUT_ROOT / "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json")["candidates"],
        load_json(OUTPUT_ROOT / "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT.json")["candidates"],
        load_json(OUTPUT_ROOT / "E3_GLOBAL_HIDDEN_DATA_BACKLOG.json")["backlog_items"],
    ]
    return [candidate for report in reports for candidate in report]


def test_required_outputs_and_master_decision_status() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    assert missing == []

    decision = load_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json")
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-HIDDEN-DATA-SCOUT-MASTER-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["scout_completed"] is True
    assert decision["no_model_guard"] == "PASS"
    assert {"A", "B", "C", "D", "E", "TRACK0"} <= set(decision["candidate_counts_by_lane"])
    assert decision["candidate_counts_by_lane"]["A"] >= 10
    assert decision["top_priority_follow_on_package_recommendations"]


def test_artifact_root_inventory_covers_required_and_recent_epoch3_roots() -> None:
    inventory = load_json(OUTPUT_ROOT / "E3_ARTIFACT_ROOT_INVENTORY.json")
    roots = {row["root"]: row for row in inventory["roots"]}

    for root in ["outputs", "manifests", "schemas", "fixtures", "tests", "scripts", "docs"]:
        assert root in roots
        assert roots[root]["exists"] is True
        assert roots[root]["file_count"] > 0

    recent = {row["label"]: row for row in inventory["recent_epoch3_roots"]}
    for label in [
        "entry_gate_fuel_gauge",
        "day1_instrumentation_harness",
        "phase2_live_exposure_coverage",
        "l1_r1_r2_outcome_calibration",
        "pre_closeout_convergence",
        "foundation_closeout",
        "master_execution_r1",
        "l2_historical_label_backfill",
        "l2_r2_forecast_authority_preflight",
        "l2_r2_offline_experiment",
    ]:
        assert recent[label]["exists"] is True

    assert inventory["output_artifact_roots_count"] >= 100


def test_every_candidate_has_refs_or_limitation_and_no_training_promotion() -> None:
    candidates = all_candidates()
    assert candidates

    for candidate in candidates:
        assert REQUIRED_CANDIDATE_FIELDS <= set(candidate), candidate["candidate_id"]
        assert candidate["source_refs"] or candidate["limitations"], candidate["candidate_id"]
        assert candidate["source_class"]
        assert candidate["promotion_status"] != "training_eligible"
        assert candidate.get("training_eligible") is False
        assert "learned" not in candidate["promotion_status"].lower()


def test_lane_a_includes_required_transition_target_families_without_label_rows() -> None:
    catalog = load_json(OUTPUT_ROOT / "E3_HIDDEN_TRANSITION_TARGET_CATALOG.json")
    families = {candidate["candidate_family"] for candidate in catalog["candidates"]}

    assert {
        "inspection_delay_v0",
        "violation_resolution_delay_v0",
        "complaint_escalation_v0",
        "watch_queue_aging_v0",
        "roadwork_overrun_v0",
        "incident_duration_v0",
        "source_record_staleness_v0",
        "asset_state_persistence_v0",
        "service_restoration_time_v0",
        "backlog_clearance_time_v0",
    } <= families
    assert catalog["no_single_snapshot_conversion"] is True
    assert all(candidate["training_eligible"] is False for candidate in catalog["candidates"])

    delta = load_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA.json")
    assert delta["new_training_rows"] == 0
    assert delta["added_fixtures"] == []
    assert "candidate inventories only" in delta["promotion_policy"]


def test_lane_reports_keep_check_case_graph_and_perception_bounded() -> None:
    check = load_json(OUTPUT_ROOT / "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json")
    case = load_json(OUTPUT_ROOT / "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json")
    graph = load_json(OUTPUT_ROOT / "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json")
    llm = load_json(OUTPUT_ROOT / "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT.json")

    assert "candidate_only" in check["counts_by_check_type"]
    assert check["resolution_breakdown"]
    assert case["aggregation_floor_status"] == "not_assessed_no_case_memory_learner"
    assert graph["distinction_policy"] == ["candidate", "reviewed", "promoted", "rejected", "disputed"]
    assert llm["perception_candidate_only"] is True
    assert llm["production_cctv_or_violation_claim_created"] is False
    assert all(
        candidate["promotion_status"] in {"blocked_policy", "candidate_inventory_only"}
        for candidate in llm["candidates"]
        if "vss" in candidate["candidate_family"]
        or "deepstream" in candidate["candidate_family"]
        or "camera" in candidate["candidate_family"]
        or "clip" in candidate["candidate_family"]
    )


def test_track0_backlog_covers_required_dimensions_and_contract_fields() -> None:
    backlog = load_json(OUTPUT_ROOT / "E3_GLOBAL_HIDDEN_DATA_BACKLOG.json")
    dimensions = set(backlog["dimensions_covered"])

    assert TRACK0_DIMENSIONS <= dimensions
    for item in backlog["backlog_items"]:
        for field in [
            "backlog_id",
            "proposed_package_id",
            "target_loop_or_mode",
            "reason",
            "evidence_found",
            "missing_inputs",
            "expected_payoff",
            "dependencies",
            "non_goals",
            "recommended_priority",
        ]:
            assert field in item, item["candidate_id"]
        assert "model training" in item["non_goals"]


def test_no_model_guard_blocks_forbidden_capabilities() -> None:
    guard = load_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_NO_MODEL_GUARD_REPORT.json")

    assert guard["status"] == "PASS"
    assert guard["new_learned_registry_entries"] == 0
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_created"] == []
    assert guard["ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_agent_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False
    assert guard["training_fuel_promotion_from_scout_outputs"] is False


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_HIDDEN_DATA_SCOUT_MASTER_R1"
    assert line_endings["crlf_paths"] == []

    paths = {entry["path"] for entry in manifest["files"]}
    for required in REQUIRED_OUTPUTS - {"HASH_MANIFEST.json"}:
        assert f"outputs/epoch3_hidden_data_scout_master_r1/{required}" in paths

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

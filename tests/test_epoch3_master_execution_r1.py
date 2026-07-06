from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_master_execution_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_master_execution_r1"
EXPECTED_STATUS = "PASS_E3_MASTER_EXECUTION_R1_WITH_LIMITATIONS"
REQUIRED_ARTIFACTS = {
    "E3_MASTER_EXECUTION_R1_DECISION.json",
    "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
    "E3_L1_R3A_ARMING_READOUT.json",
    "E3_L1_R3B_ARMING_READOUT.json",
    "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json",
    "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
    "E3_L2_R1_TARGET_SUFFICIENCY_REPORT.json",
    "E3_L2_R2_ARMING_READOUT.json",
    "E3_Q3_PROPAGATION_RULE_OWNERSHIP_DECISION.json",
    "E3_Q6_UNCERTAINTY_EXTENSION_DECISION.json",
    "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json",
    "E3_R0_2_UNCERTAINTY_CONSUMER_IMPACT_ASSESSMENT.json",
    "E3_R0_2_SHARED_VALIDATOR_UPDATE_REPORT.json",
    "E3_R0_2_UNCERTAINTY_FIXTURES_REPORT.json",
    "E3_R0_2_HASH_MANIFEST.json",
    "E3_R0_2_CONTRACT_PUBLICATION_ROW.json",
    "E3_L3_COUNTERFACTUAL_PACKET_SCHEMA.json",
    "E3_L3_COUNTERFACTUAL_ASSUMPTIONS_SCHEMA.json",
    "E3_L3_COUNTERFACTUAL_UNCERTAINTY_SCHEMA.json",
    "E3_L3_PROPAGATION_RULE_REGISTRY.json",
    "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json",
    "E3_L3_COUNTERFACTUAL_CHECK_GATE_REPORT.json",
    "E3_L3_COUNTERFACTUAL_MINIMUM_PATH_REPORT.json",
    "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION.json",
    "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json",
    "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION.json",
    "E3_L4_SOURCE_CLASS_OUTCOME_LINEAGE_REPORT.json",
    "E3_L4_ARMING_READOUT.json",
    "E3_FUEL_GENERATION_PROGRAM.md",
    "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json",
    "E3_FUEL_RATE_ESTIMATE.json",
    "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE.json",
    "E3_CLOSEOUT_DECISION_DATE_ROW.json",
    "E3_EXECUTION_R1_CORPUS_DELTA.json",
    "E3_NO_MODEL_GUARD_REPORT.json",
    "E3_EXECUTION_R1_LIMITATIONS.json",
    "E3_EXECUTION_R1_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}
FORBIDDEN = {
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_required_artifacts_and_decision_status() -> None:
    published = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    decision = load_json(OUTPUT_ROOT / "E3_MASTER_EXECUTION_R1_DECISION.json")

    assert REQUIRED_ARTIFACTS <= published
    assert decision["task_id"] == "MAIN-CITYBRAIN-EPOCH3-MASTER-EXECUTION-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["blockers"] == []
    assert decision["evaluator_is_only_arming_authority"] is True
    assert decision["mid_run_arming_rule"] == "ledger_row_only_no_model_start_in_same_run"
    assert set(decision["tracks"]) == {
        "A_loop1_readout",
        "B_baseline_backtest",
        "C_counterfactual_minimum_path",
        "D_l4_unblockers",
        "E_fuel_generation_program",
    }


def test_evaluator_snapshot_and_track_a_readouts_do_not_recompute_thresholds() -> None:
    snapshot = load_json(OUTPUT_ROOT / "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json")
    r3a = load_json(OUTPUT_ROOT / "E3_L1_R3A_ARMING_READOUT.json")
    r3b = load_json(OUTPUT_ROOT / "E3_L1_R3B_ARMING_READOUT.json")

    assert snapshot["evaluator_is_only_arming_authority"] is True
    assert snapshot["evaluator_rerun"] is True
    assert snapshot["threshold_crossing_does_not_start_work_in_same_run"] is True
    assert snapshot["mid_run_arming_events"] == []
    assert snapshot["mid_run_arming_ledger_rows"] == []
    assert set(snapshot["not_armed"]) == FORBIDDEN

    for readout, capability in [
        (r3a, "L1.R3A_OFFLINE_RANKER_EXPERIMENT"),
        (r3b, "L1.R3B_OPERATOR_FACING_LEARNED_RANKING"),
    ]:
        assert readout["capability_id"] == capability
        assert readout["snapshot_id"] == "e3_snapshot_foundation_closeout_001"
        assert readout["snapshot_ref"] == "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_ARMING_STATUS_FINAL.json"
        assert readout["thresholds_not_reimplemented"] is True
        assert readout["armed"] is False
        assert readout["failed_requirement_ids"]


def test_track_b_target_label_definition_and_baseline_are_no_model() -> None:
    target = load_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json")
    backtest = load_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT.json")
    sufficiency = load_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_SUFFICIENCY_REPORT.json")
    l2r2 = load_json(OUTPUT_ROOT / "E3_L2_R2_ARMING_READOUT.json")

    assert target["target_id"] == "permit_stall_v0"
    assert target["cities"] == ["NYC", "London"]
    assert target["threshold_days_in_non_terminal_state"] == 60
    assert target["states_counted"]
    assert target["terminal_outcomes"]
    assert target["model_allowed"] is False

    assert backtest["target_label_definition_ref"] == "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json"
    assert backtest["forecast_model_created"] is False
    assert backtest["forecast_packet_model_output_created"] is False
    assert backtest["no_model_assertion"] is True
    assert backtest["status"] == "PASS_BASELINE_BACKTEST_REPORT_WITH_LABEL_LIMITATIONS"
    assert sufficiency["label_history_sufficient"] is False
    assert l2r2["thresholds_not_reimplemented"] is True
    assert l2r2["armed"] is False
    assert "L2R2_LABEL_HISTORY_SUFFICIENT" in l2r2["failed_requirement_ids"]


def test_track_c_q3_q6_r02_and_counterfactual_example() -> None:
    q3 = load_json(OUTPUT_ROOT / "E3_Q3_PROPAGATION_RULE_OWNERSHIP_DECISION.json")
    q6 = load_json(OUTPUT_ROOT / "E3_Q6_UNCERTAINTY_EXTENSION_DECISION.json")
    delta = load_json(OUTPUT_ROOT / "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json")
    impact = load_json(OUTPUT_ROOT / "E3_R0_2_UNCERTAINTY_CONSUMER_IMPACT_ASSESSMENT.json")
    validator = load_json(OUTPUT_ROOT / "E3_R0_2_SHARED_VALIDATOR_UPDATE_REPORT.json")
    fixtures = load_json(OUTPUT_ROOT / "E3_R0_2_UNCERTAINTY_FIXTURES_REPORT.json")
    publication = load_json(OUTPUT_ROOT / "E3_R0_2_CONTRACT_PUBLICATION_ROW.json")
    packet = load_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json")
    check_gate = load_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_CHECK_GATE_REPORT.json")
    minimum = load_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_MINIMUM_PATH_REPORT.json")

    assert q3["status"] == "PUBLISHED"
    assert "Semantic Graph v2" in q3["semantic_graph_v2_substrate_ref"]
    assert q6["decision"] == "R0.2_additive_uncertainty_extension"
    assert delta["contract_version"] == "R0.2"
    assert impact["consumer_breakage_expected"] is False
    assert validator["shared_validator_updated"] is True
    assert fixtures["fixture_count"] >= 2
    assert publication["track_c_schemas_build_against"] == "R0.2"

    assert packet["mode"] == "counterfactual_review_only"
    assert packet["learned_model_used"] is False
    assert packet["no_action_claim"] is True
    assert packet["uncertainty"]["contract_version"] == "R0.2"
    assert check_gate["status"] == "PASS"
    assert minimum["deterministic_replay_based"] is True
    assert minimum["counterfactual_learner_created"] is False


def test_track_d_l4_erasure_metric_split_and_readout() -> None:
    split = load_json(OUTPUT_ROOT / "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION.json")
    workflow = load_json(OUTPUT_ROOT / "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION.json")
    enforcement = load_json(OUTPUT_ROOT / "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json")
    lineage = load_json(OUTPUT_ROOT / "E3_L4_SOURCE_CLASS_OUTCOME_LINEAGE_REPORT.json")
    readout = load_json(OUTPUT_ROOT / "E3_L4_ARMING_READOUT.json")

    assert split["new_e3_blocking_metric"] == (
        "policy.right_to_forget_or_delete_path.erasure_workflow_defined_and_enforced_at_current_scope"
    )
    assert split["future_production_metric"] == "policy.right_to_forget_or_delete_path.production_erasure_workflow"
    assert split["l4_requirement_repointed"] is True
    assert split["production_erasure_may_remain_false_without_blocking_e3_l4_minimum"] is True
    assert workflow["production_erasure_workflow"] is False
    assert enforcement["learned_case_memory_created"] is False
    assert lineage["status"] == "PASS_WITH_LIMITATIONS"
    assert readout["thresholds_not_reimplemented"] is True
    assert readout["armed"] is False
    assert readout["production_erasure_not_e3_blocker"] is True
    assert "policy.right_to_forget_or_delete_path.production_erasure_workflow" == readout["future_production_metric"]


def test_track_e_fuel_program_is_stratified_and_date_is_default() -> None:
    protocol = load_json(OUTPUT_ROOT / "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json")
    estimate = load_json(OUTPUT_ROOT / "E3_FUEL_RATE_ESTIMATE.json")
    weekly = load_json(OUTPUT_ROOT / "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE.json")
    date_row = load_json(OUTPUT_ROOT / "E3_CLOSEOUT_DECISION_DATE_ROW.json")

    operators = set(protocol["operator_refs"])
    families = set(protocol["eligible_non_holdout_families"])
    cells = {(row["operator_ref"], row["watch_family"]) for row in protocol["weekly_snapshot_template_cells"]}

    assert protocol["minimum_operator_refs"] == 3
    assert protocol["stratification_required"] is True
    assert "all eligible non-holdout families" in protocol["rule"]
    assert protocol["holdout_families"] == ["media_candidate"]
    assert cells == {(op, family) for op in operators for family in families}
    assert estimate["estimated_items_per_week_low"] == 60
    assert estimate["estimated_items_per_week_high"] == 90
    assert estimate["fine_grained_cells_per_week"] == len(cells)
    assert weekly["required_cells"] == protocol["weekly_snapshot_required_cells"]
    assert date_row["closeout_decision_date"] == "2026-08-31"


def test_corpus_delta_no_model_guard_limitations_and_ledger() -> None:
    delta = load_json(OUTPUT_ROOT / "E3_EXECUTION_R1_CORPUS_DELTA.json")
    guard = load_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json")
    limitations = load_json(OUTPUT_ROOT / "E3_EXECUTION_R1_LIMITATIONS.json")
    ledger = load_json(OUTPUT_ROOT / "E3_EXECUTION_R1_LEDGER_ROW.json")

    for artifact in [
        "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
        "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json",
        "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json",
        "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json",
    ]:
        assert artifact in delta["registered_artifacts"]

    assert guard["status"] == "PASS"
    assert guard["ranker_created"] is False
    assert guard["operator_facing_ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["forecast_packet_model_output_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_agent_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_armed"] == []

    assert limitations["status"] == "PASS_WITH_LIMITATIONS"
    assert ledger["status"] == EXPECTED_STATUS
    assert ledger["mid_run_arming_started_new_work"] is False


def test_schemas_and_manifests_are_present() -> None:
    for path in [
        "schemas/arming_readout.schema.json",
        "schemas/counterfactual_example_packet.schema.json",
        "schemas/fuel_generation_protocol.schema.json",
        "schemas/l4_erasure_metric_split.schema.json",
        "schemas/permit_stall_label_definition.schema.json",
        "manifests/epoch3_master_execution_r1_package_tracks.json",
        "manifests/epoch3_master_execution_r1_required_output_artifacts.json",
    ]:
        assert (REPO_ROOT / path).exists(), path
        load_json(REPO_ROOT / path)


def test_hash_manifests_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    r02_manifest = load_json(OUTPUT_ROOT / "E3_R0_2_HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_MASTER_EXECUTION_R1"
    assert line_endings["crlf_paths"] == []
    assert REQUIRED_ARTIFACTS - {"HASH_MANIFEST.json"} <= {Path(entry["path"]).name for entry in manifest["files"]}

    for manifest_payload in [manifest, r02_manifest]:
        for entry in manifest_payload["files"]:
            path = REPO_ROOT / entry["path"]
            assert path.exists(), entry["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]


def test_all_generated_json_parses() -> None:
    for path in OUTPUT_ROOT.glob("*.json"):
        load_json(path)

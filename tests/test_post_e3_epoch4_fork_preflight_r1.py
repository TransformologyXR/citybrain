from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_post_e3_epoch4_fork_preflight_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "post_e3_epoch4_fork_preflight_r1"
PUBLICATION_DIR = REPO_ROOT / "publications" / "post_e3" / "main-citybrain-post-e3-closeout-epoch4-fork-preflight-r1"
EXPECTED_STATUS = "PASS_POST_E3_EPOCH4_FORK_PREFLIGHT_R1_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = {
    "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION.json",
    "POST_E3_CLOSEOUT_ARTIFACT_READINESS_REPORT.json",
    "E4_FORK_DECISION_TEMPLATE.json",
    "E4_ARMING_INHERITANCE_HANDOFF.json",
    "E4_GO_LIVE_REVIEW_PILOT_PATH_SPEC.json",
    "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json",
    "E4_HYBRID_PATH_SPEC.json",
    "E4_DEFERRED_PATH_SPEC.json",
    "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST.json",
    "E4_BACKLOG_HANDOFF.json",
    "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "E4_PUBLICATION_GOVERNANCE_CONTINUITY_ROW.json",
    "POST_E3_EPOCH4_FORK_LIMITATIONS.json",
    "POST_E3_EPOCH4_FORK_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_preflight_decision_is_pass_with_no_epoch4_start() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    assert missing == []

    decision = load_json(OUTPUT_ROOT / "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION.json")
    assert decision["package_id"] == "MAIN-CITYBRAIN-POST-E3-CLOSEOUT-EPOCH4-FORK-PREFLIGHT-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["closeout_type"] == "POST_E3_PREPARATION_NOT_EPOCH4_START"
    assert decision["human_fork_decision_made"] is False
    assert decision["human_fork_decision_required"] is True
    assert decision["selected_fork"] is None
    assert decision["epoch4_started"] is False
    assert decision["new_models_created"] == 0
    assert decision["new_training_rows_created"] == 0
    assert decision["new_learned_registry_entries"] == 0
    assert decision["forbidden_capabilities_created"] == []


def test_closeout_readiness_uses_durable_publication_home() -> None:
    readiness = load_json(OUTPUT_ROOT / "POST_E3_CLOSEOUT_ARTIFACT_READINESS_REPORT.json")

    assert readiness["status"] == "PASS_E3_CLOSEOUT_PUBLICATION_HOME_READY"
    assert readiness["e3_closeout_package_id"] == "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"
    assert readiness["e3_closeout_status"] == "PASS_E3_CLOSEOUT_WITH_LIMITATIONS"
    assert readiness["publication_home_durable"] is True
    assert readiness["missing_durable_artifacts"] == []
    assert readiness["durable_artifact_count"] == readiness["artifact_count"]
    assert all(row["durable_in_publication_home"] for row in readiness["artifacts"])


def test_fork_decision_template_is_human_owned_and_unselected() -> None:
    template = load_json(OUTPUT_ROOT / "E4_FORK_DECISION_TEMPLATE.json")

    assert template["decision_owner"] == "human_product_owner"
    assert template["decision_required"] is True
    assert template["selected_value"] is None
    assert template["codex_may_select_value"] is False
    assert template["epoch4_started_by_this_template"] is False
    assert template["allowed_values"] == [
        "GO_LIVE_REVIEW_PILOT",
        "NONLIVE_MECHANICAL_BACKLOG",
        "HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG",
        "DEFER_EPOCH4_START",
    ]


def test_all_four_paths_are_defined_without_silent_arming() -> None:
    live = load_json(OUTPUT_ROOT / "E4_GO_LIVE_REVIEW_PILOT_PATH_SPEC.json")
    nonlive = load_json(OUTPUT_ROOT / "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json")
    hybrid = load_json(OUTPUT_ROOT / "E4_HYBRID_PATH_SPEC.json")
    deferred = load_json(OUTPUT_ROOT / "E4_DEFERRED_PATH_SPEC.json")

    assert live["operator_or_structured_review_fuel_can_accumulate"] is True
    assert live["human_selection_required"] is True
    assert nonlive["operator_or_structured_review_fuel_can_accumulate"] is False
    assert nonlive["nonlive_mechanical_work_allowed"] is True
    assert "R3A/R3B/L4" in nonlive["blocked_fuel_effect"]
    assert hybrid["operator_or_structured_review_fuel_can_accumulate"] is True
    assert "provenance-separated" in hybrid["separation_rule"]
    assert deferred["nonlive_mechanical_work_allowed"] is False
    assert deferred["operator_or_structured_review_fuel_can_accumulate"] is False

    for spec in [live, nonlive, hybrid, deferred]:
        assert spec["selected_by_this_package"] is False
        assert spec["epoch4_started_by_this_package"] is False
        assert spec["can_arm_r3a_r3b_l4_from_codex_only"] is False
        assert spec["product_forecast_surface_allowed"] is False


def test_epoch3_arming_inheritance_is_explicit_and_unchanged() -> None:
    handoff = load_json(OUTPUT_ROOT / "E4_ARMING_INHERITANCE_HANDOFF.json")

    assert handoff["inherits_from"] == "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"
    assert handoff["evaluator_inherited"] is True
    assert handoff["thresholds_inherited"] is True
    assert handoff["fuel_gauge_snapshot_chain_inherited"] is True
    assert handoff["no_model_guard_cadence_inherited"] is True
    assert handoff["thresholds_changed"] is False
    assert handoff["threshold_changes_require_governance_delta"] is True
    assert handoff["codex_work_can_substitute_for_operator_dispositions"] is False
    assert "L1.R3B_OPERATOR_FACING_LEARNED_RANKING" in handoff["deferred_capabilities"]
    assert "L4_CASE_MEMORY" in handoff["deferred_capabilities"]


def test_sequence_and_backlog_are_conditional() -> None:
    sequence = load_json(OUTPUT_ROOT / "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST.json")
    backlog = load_json(OUTPUT_ROOT / "E4_BACKLOG_HANDOFF.json")

    assert sequence["depends_on_human_fork_decision"] is True
    assert sequence["selected_sequence"] is None
    assert len(sequence["if_GO_LIVE_REVIEW_PILOT"]) >= 1
    assert len(sequence["if_NONLIVE_MECHANICAL_BACKLOG"]) >= 1
    assert len(sequence["if_HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG"]) >= 1
    assert len(sequence["if_DEFER_EPOCH4_START"]) >= 1

    assert "operator_fuel_program" in backlog["live_review_pilot_dependent"]
    assert any("city-stratified forecast" in item for item in backlog["nonlive_mechanical"])
    assert "dynamic investigation" in backlog["parked"]
    assert backlog["operator_fuel_blocked_without_live_or_review_pilot"] is True
    assert backlog["nonlive_work_cannot_close_ranking_or_memory_loops"] is True


def test_no_forbidden_capability_guard_carries_forecast_status_forward() -> None:
    guard = load_json(OUTPUT_ROOT / "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json")
    limitations = load_json(OUTPUT_ROOT / "POST_E3_EPOCH4_FORK_LIMITATIONS.json")

    assert guard["status"] == "PASS"
    assert guard["allowed_existing_experimental_component"] == "forecast.permit_stall_v0.r1"
    assert guard["new_models_created"] == 0
    assert guard["new_training_rows_created"] == 0
    assert guard["new_learned_registry_entries"] == 0
    assert guard["product_forecast_surface_created"] is False
    assert guard["product_forecast_packet_created"] is False
    assert guard["ranker_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False
    assert guard["forbidden_capabilities_created"] == []
    assert any("frozen-replay-only" in item for item in limitations["limitations"])


def test_publication_copy_is_durable_and_hashes_verify() -> None:
    continuity = load_json(OUTPUT_ROOT / "E4_PUBLICATION_GOVERNANCE_CONTINUITY_ROW.json")

    assert PUBLICATION_DIR.exists()
    assert continuity["status"] == "PASS"
    assert continuity["outputs_are_gitignored_and_not_authoritative"] is True
    assert continuity["publication_home_required_for_governance_artifacts"] is True
    assert continuity["publication_lf_rule_present"] is True

    missing_publication = [name for name in REQUIRED_OUTPUTS if not (PUBLICATION_DIR / name).exists()]
    assert missing_publication == []

    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")
    assert line_endings["status"] == "PASS_LF_STABLE_FOR_POST_E3_EPOCH4_FORK_PREFLIGHT_R1"
    assert line_endings["crlf_paths"] == []

    paths = {entry["path"] for entry in manifest["files"]}
    for required in REQUIRED_OUTPUTS - {"HASH_MANIFEST.json"}:
        assert f"outputs/post_e3_epoch4_fork_preflight_r1/{required}" in paths

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

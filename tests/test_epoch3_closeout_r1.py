from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_closeout_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_closeout_r1"
PUBLICATION_ROOT = REPO_ROOT / "publications" / "epoch3"
EXPECTED_STATUS = "PASS_E3_CLOSEOUT_WITH_LIMITATIONS"
EXPECTED_CLOSEOUT_TYPE = "MINIMUM_ACCEPTABLE_WITH_LOOP2_OFFLINE_EXPERIMENT"

REQUIRED_OUTPUTS = {
    "E3_CLOSEOUT_DECISION.json",
    "E3_PUBLICATION_HOME_SWEEP_REPORT.json",
    "E3_MASTER_LEDGER.json",
    "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json",
    "E3_LOOP_CLOSEOUT_TABLE.json",
    "E3_FORECAST_RESULT_FRAMING_ROW.json",
    "E3_CITY_DIVERGENCE_WARNING_ROW.json",
    "E3_ARMING_HANDOFF_TO_EPOCH4.json",
    "E3_EPOCH4_FORK_DECISION_ROW.json",
    "E3_FUEL_REALITY_FINDING_ROW.json",
    "E3_NO_FORBIDDEN_CAPABILITY_AUDIT.json",
    "E3_CLOSEOUT_LIMITATIONS.json",
    "E3_CLOSEOUT_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}

CHAIN_PACKAGE_COUNT = 14


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_closeout_decision_and_required_outputs() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    assert missing == []

    decision = load_json(OUTPUT_ROOT / "E3_CLOSEOUT_DECISION.json")
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["closeout_type"] == EXPECTED_CLOSEOUT_TYPE
    assert decision["foundation_closed"] is True
    assert decision["full_ideal_closeout"] is False
    assert decision["system_live"] is False
    assert decision["operator_fuel_program"] == "deferred_not_live"
    assert decision["forecast_pipeline_validated"] is True
    assert decision["forecast_product_ready"] is False
    assert decision["no_forbidden_capability_audit"] == "PASS"


def test_publication_home_sweep_covers_full_chain_and_lf_rule() -> None:
    sweep = load_json(OUTPUT_ROOT / "E3_PUBLICATION_HOME_SWEEP_REPORT.json")

    assert PUBLICATION_ROOT.exists()
    assert sweep["publication_root"] == "publications/epoch3"
    assert sweep["retroactive"] is True
    assert sweep["lf_pinning_present"] is True
    assert sweep["full_epoch3_chain_covered"] is True
    assert sweep["packages_expected"] == CHAIN_PACKAGE_COUNT
    assert sweep["packages_published"] == CHAIN_PACKAGE_COUNT
    assert all(row["publication_path"] for row in sweep["packages"])
    assert all((REPO_ROOT / row["publication_path"]).exists() for row in sweep["packages"])
    assert any(row["package_id"] == "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1" for row in sweep["packages"])

    gitattributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "publications/** text eol=lf" in gitattributes


def test_master_ledger_lists_every_epoch3_package() -> None:
    ledger = load_json(OUTPUT_ROOT / "E3_MASTER_LEDGER.json")

    assert ledger["status"] == "PASS_WITH_LIMITATIONS"
    assert ledger["must_cover_full_epoch3_chain"] is True
    assert ledger["covered_package_count"] == CHAIN_PACKAGE_COUNT
    assert len(ledger["rows"]) == CHAIN_PACKAGE_COUNT
    assert {"foundation_closeout", "execution", "scout", "final_closeout"} <= set(ledger["categories"])

    by_id = {row["package_id"]: row for row in ledger["rows"]}
    closeout = by_id["MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"]
    assert closeout["status"] == EXPECTED_STATUS
    assert closeout["publication_path"].endswith("main-citybrain-epoch3-closeout-r1")
    assert closeout["proof_artifacts"]
    assert closeout["boundary_outcome"] == "no_product_learned_capabilities_armed"


def test_learned_component_snapshot_allows_exactly_one_experiment() -> None:
    snapshot = load_json(OUTPUT_ROOT / "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json")

    comps = snapshot["allowed_experimental_components"]
    assert len(comps) == 1
    component = comps[0]
    assert component["component_id"] == "forecast.permit_stall_v0.r1"
    assert component["component_kind"] == "forecast_model"
    assert component["status"] == "experimental"
    assert component["consuming_surfaces"] == []
    assert component["frozen_replay_only"] is True
    assert component["release_ledger_row"] is None
    assert component["product_surface_created"] is False
    assert snapshot["forbidden_components_created"] == 0
    assert snapshot["new_components_in_closeout_package"] == 0


def test_forecast_framing_and_city_divergence_are_honest() -> None:
    forecast = load_json(OUTPUT_ROOT / "E3_FORECAST_RESULT_FRAMING_ROW.json")
    city = load_json(OUTPUT_ROOT / "E3_CITY_DIVERGENCE_WARNING_ROW.json")

    assert forecast["headline"] == "pipeline_validated_model_not_deployable"
    assert forecast["pipeline_validated"] is True
    assert forecast["specific_r1_model_deployable"] is False
    assert forecast["average_precision"]["model"] == 0.191775
    assert forecast["average_precision"]["baseline_proxy"] == 0.107386
    assert forecast["average_precision"]["interpretation"] == "real_offline_improvement"
    assert forecast["brier"]["improved"] is True
    assert forecast["recall_at_fixed_precision_limitation"] == "weak"
    assert forecast["product_surface_armed"] is False
    assert forecast["operator_facing_forecast_armed"] is False

    assert city["status"] == "WARNING"
    assert city["london_stall_rate"] != city["nyc_stall_rate"]
    assert city["supports_cross_city_learned_transfer_parking"] is True
    assert city["cross_city_learned_transfer_status"] == "parked"
    assert city["epoch4_requirement"] == "city_stratified_l2_forecast_improvement"


def test_arming_handoff_fuel_reality_and_epoch4_fork() -> None:
    handoff = load_json(OUTPUT_ROOT / "E3_ARMING_HANDOFF_TO_EPOCH4.json")
    fuel = load_json(OUTPUT_ROOT / "E3_FUEL_REALITY_FINDING_ROW.json")
    fork = load_json(OUTPUT_ROOT / "E3_EPOCH4_FORK_DECISION_ROW.json")

    assert "arming_status_evaluator" in handoff["inherited_infrastructure"]
    assert "fuel_gauge_snapshot_chain" in handoff["inherited_infrastructure"]
    assert "no_model_guard_cadence" in handoff["inherited_infrastructure"]
    assert handoff["thresholds_relitigated_in_epoch4"] is False
    assert handoff["governance_delta_required_to_change_thresholds"] is True
    assert handoff["operator_paced_fuel_program"] == "deferred_not_live"

    assert fuel["system_live"] is False
    assert fuel["operator_paced_fuel_accumulated"] is False
    assert fuel["ranking_armed"] is False
    assert fuel["case_memory_armed"] is False
    assert "correct governance" in fuel["interpretation"]

    fork_ids = {row["id"] for row in fork["forks"]}
    assert {"GO_LIVE_OR_REVIEW_PILOT", "NON_LIVE_MECHANICAL_BACKLOG"} <= fork_ids
    non_live = next(row for row in fork["forks"] if row["id"] == "NON_LIVE_MECHANICAL_BACKLOG")
    assert any("city-stratified L2" in item for item in non_live["backlog_items"])


def test_no_forbidden_capability_audit_is_strict() -> None:
    audit = load_json(OUTPUT_ROOT / "E3_NO_FORBIDDEN_CAPABILITY_AUDIT.json")

    assert audit["status"] == "PASS"
    assert audit["allowed_existing_experimental_component"] == "forecast.permit_stall_v0.r1"
    assert audit["new_model_training_created"] is False
    assert audit["new_learned_registry_entries"] == 0
    assert audit["ranker_created"] is False
    assert audit["operator_facing_forecast_created"] is False
    assert audit["product_forecast_surface_created"] is False
    assert audit["product_forecast_packet_created"] is False
    assert audit["case_memory_learner_created"] is False
    assert audit["counterfactual_learner_created"] is False
    assert audit["dynamic_investigation_created"] is False
    assert audit["cross_city_learned_transfer_created"] is False
    assert audit["official_action_or_dispatch_created"] is False


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_CLOSEOUT_R1"
    assert line_endings["crlf_paths"] == []

    paths = {entry["path"] for entry in manifest["files"]}
    for required in REQUIRED_OUTPUTS - {"HASH_MANIFEST.json"}:
        assert f"outputs/epoch3_closeout_r1/{required}" in paths

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

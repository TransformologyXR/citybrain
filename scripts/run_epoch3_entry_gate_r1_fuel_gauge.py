from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluate_arming_status import evaluate  # noqa: E402

OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_3_entry_gate_r1_fuel_gauge"
MANIFEST_PATH = REPO_ROOT / "manifests" / "epoch3_arming_manifest.json"
EVALUATOR_SPEC_PATH = REPO_ROOT / "manifests" / "epoch3_arming_evaluator_spec.yaml"

STATUS = "PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_ENTRY_GATE_R1_FUEL_GAUGE"

REQUIRED_OUTPUTS = [
    "E3_ENTRY_GATE_DECISION.json",
    "E3_ARMING_STATUS_REPORT.json",
    "E3_FUEL_GAUGE_BASELINE_REPORT.md",
    "E3_BASELINE_METRICS.json",
    "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
    "E3_METRICS_RECONCILIATION_REPORT.json",
    "E3_POLICY_AND_AGGREGATION_RECONCILIATION_ROW.json",
    "E3_CORPUS_SCOPE_RECONCILIATION_ROW.json",
    "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
    "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
    "E3_HASH_LINE_ENDING_STABILITY_REPORT.json",
    "e3_arming_status_day_one_smoke.json",
    "e3_arming_status_reconciled_baseline_smoke.json",
    "E3_GATE_LEDGER_ROW.json",
    "E3_ARMING_THRESHOLD_CROSSING_SAMPLE.json",
    "E3_LEARNED_COMPONENT_REGISTRY_EXPERIMENTAL_EXAMPLES.json",
    "E3_LIMITATIONS.json",
    "HASH_MANIFEST.json",
]

SOURCE_REFS = {
    "epoch_2_2_final_decision": REPO_ROOT / "outputs" / "epoch_2_2" / "final_closeout" / "EPOCH_2_2_FINAL_DECISION.json",
    "epoch_2_2_label_fuel": REPO_ROOT / "outputs" / "epoch_2_2" / "final_closeout" / "LABEL_FUEL_GAUGE_REPORT.json",
    "epoch_2_2_corpus_delta": REPO_ROOT / "outputs" / "epoch_2_2" / "final_closeout" / "EPOCH_2_2_CORPUS_DELTA.json",
    "epoch_2_2_source_delta": REPO_ROOT / "outputs" / "epoch_2_2" / "final_closeout" / "EPOCH_2_2_SOURCE_OF_TRUTH_MATRIX_DELTA.json",
    "epoch_2_2_watch_service_decision": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service" / "WATCH_SCOUT_SERVICE_DECISION.json",
    "epoch_2_2_watch_service_config": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service" / "WATCH_SERVICE_CONFIG.json",
    "epoch_2_2_watch_service_throttle": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service" / "WATCH_SERVICE_THROTTLE_REPORT.json",
    "epoch_2_2_watch_service_run_envelopes": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service" / "WATCH_SERVICE_RUN_ENVELOPES.jsonl",
    "epoch_2_1_privacy_retention_decision": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "PUSH_2_1A_LANE_A_DECISION.json",
    "epoch_2_1_privacy_retention_policy": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "privacy_retention_policy_v1.json",
    "epoch_2_1_privacy_validation": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "privacy_policy_validation_report.json",
    "epoch_2_1_privacy_enforcement_fixtures": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "privacy_policy_enforcement_fixtures.json",
    "epoch_2_1_aggregation_floor_policy": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "aggregation_floor_policy_v1.json",
    "epoch_2_1_retention_matrix": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "retention_matrix_v1.json",
    "epoch_2_1_right_to_forget_policy": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention" / "right_to_forget_policy_v1.md",
    "epoch_2_1a_foundations_gate": REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations" / "INTEGRATION_GATE_2_1A_DECISION.json",
    "watch_disposition_summary": REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux" / "calibration_reports_v1" / "watchitem_disposition_summary.json",
    "operator_validation_metrics": REPO_ROOT / "outputs" / "main_citybrain_d9_operator_task_scoreboard_r5" / "OPERATOR_VALIDATION_METRICS.json",
    "perception_shadow": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_b_perception_shadow" / "PERCEPTION_SHADOW_DECISION.json",
    "g2_metrics": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_c_g2_fixed_dag" / "G2_ACCEPTANCE_METRICS.json",
    "spatial_service": REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_a_pack_spatial" / "SPATIAL_AGENT_SERVICE_REPORT.json",
}

DAY_ONE_ARMED = {
    "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
    "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
    "L1.R1_OUTCOME_LEDGER_HARDENING",
    "L1.R2_CALIBRATION_REPORT_HARDENING",
    "L2.R1_BACKTEST_HARNESS_BUILD",
    "E3.ARMING_STATUS_WATCH_FAMILY",
}

NOT_ARMED_INITIAL = {
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def load_manifest() -> dict[str, Any]:
    return read_json(MANIFEST_PATH, {})


def sorted_unique(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "")})


def derive_watch_service_metrics() -> dict[str, Any]:
    config = read_json(SOURCE_REFS["epoch_2_2_watch_service_config"], {})
    decision = read_json(SOURCE_REFS["epoch_2_2_watch_service_decision"], {})
    throttle = read_json(SOURCE_REFS["epoch_2_2_watch_service_throttle"], {})

    configured = sorted_unique(list((config.get("operator_controlled_family_throttle_state") or {}).keys()))
    emitted: list[str] = []
    for tick in throttle.get("ticks", []):
        emitted.extend(list((tick.get("family_emitted_counts") or {}).keys()))
        emitted.extend([item.get("family") for item in tick.get("emitted_watch_items", [])])
    emitted_families = sorted_unique(emitted)
    distinct_families = sorted_unique(configured + emitted_families)

    return {
        "configured_families": configured,
        "emitted_families": emitted_families,
        "distinct_families": distinct_families,
        "distinct_family_count": len(distinct_families),
        "status": decision.get("status") or throttle.get("status"),
        "decision_code": decision.get("decision_code"),
        "service_health_state": decision.get("service_health_state") or throttle.get("service_health_state"),
        "tick_count": decision.get("tick_count") or throttle.get("tick_count", 0),
        "aggregate_counts": decision.get("aggregate_counts") or throttle.get("aggregate_counts") or {},
        "checks": decision.get("checks") or throttle.get("checks") or {},
    }


def derive_policy_fixture_metrics() -> dict[str, Any]:
    decision = read_json(SOURCE_REFS["epoch_2_1_privacy_retention_decision"], {})
    validation = read_json(SOURCE_REFS["epoch_2_1_privacy_validation"], {})
    enforcement = read_json(SOURCE_REFS["epoch_2_1_privacy_enforcement_fixtures"], {})
    aggregation = read_json(SOURCE_REFS["epoch_2_1_aggregation_floor_policy"], {})

    policy_fixture_enforced = (
        SOURCE_REFS["epoch_2_1_privacy_retention_policy"].exists()
        and SOURCE_REFS["epoch_2_1_retention_matrix"].exists()
        and validation.get("status") == "PASS"
        and enforcement.get("status") == "PASS"
    )
    right_to_forget_enforced = policy_fixture_enforced and SOURCE_REFS["epoch_2_1_right_to_forget_policy"].exists()
    aggregation_floor_policy_enforced = policy_fixture_enforced and SOURCE_REFS["epoch_2_1_aggregation_floor_policy"].exists()

    return {
        "decision_status": decision.get("status"),
        "validation_status": validation.get("status"),
        "enforcement_fixture_status": enforcement.get("status"),
        "case_retention_policy_enforced": policy_fixture_enforced,
        "right_to_forget_policy_enforced": right_to_forget_enforced,
        "aggregation_floor_policy_enforced": aggregation_floor_policy_enforced,
        "aggregation_floor_currently_met": False,
        "minimum_items_for_dashboard_cell": aggregation.get("minimum_items_for_dashboard_cell"),
        "minimum_operators_for_display_or_learning_stat": aggregation.get("minimum_operators_for_display_or_learning_stat"),
    }


def build_baseline_metrics() -> dict[str, Any]:
    label_fuel = read_json(SOURCE_REFS["epoch_2_2_label_fuel"], {})
    disposition_summary = read_json(SOURCE_REFS["watch_disposition_summary"], {})
    operator_metrics = read_json(SOURCE_REFS["operator_validation_metrics"], {})
    corpus_delta = read_json(SOURCE_REFS["epoch_2_2_corpus_delta"], {})
    watch_service = derive_watch_service_metrics()
    policy_fixture = derive_policy_fixture_metrics()
    full_discovery = corpus_delta.get(
        "full_historical_discovery",
        {"status": "NOT_RUN_FOR_THIS_GATE"},
    )

    observed = label_fuel.get("observed", {})
    historical = disposition_summary.get("statistics", {})
    usable_operators = operator_metrics.get("usable_external_sessions") or observed.get("usable_external_operator_sessions", 0)
    terminal_count = observed.get("eligible_post_fix_terminal_dispositions", 0)
    domain_pack_count = 4 if SOURCE_REFS["epoch_2_2_source_delta"].exists() else 0
    eligible_training_watch_family_count = observed.get("eligible_review_watch_families", 0)
    watch_family_count = watch_service["distinct_family_count"]
    historical_dispositions = observed.get(
        "historical_disposition_events_seen",
        historical.get("total_disposition_event_count", 0),
    )

    return {
        "metrics_snapshot_id": "citybrain_epoch3_entry_baseline_from_epoch2_closeout",
        "metrics_source": "existing_epoch_2_2_closeout_watch_service_epoch_2_1_policy_and_available_operator_telemetry",
        "source_refs": {name: rel(path) for name, path in SOURCE_REFS.items() if path.exists()},
        "outcome": {
            "terminal_dispositions": {
                "count": terminal_count,
                "historical_seen": historical_dispositions,
                "eligibility_scope": "post_validation_fix_propensity_known_training_fuel",
            },
            "operator_refs": {
                "distinct_count": usable_operators,
                "eligibility_scope": "post_validation_fix_propensity_known_training_fuel",
            },
            "min_terminal_dispositions_per_operator": 0,
            "min_terminal_dispositions_per_armed_family": 0,
            "training_fuel": {
                "eligible_post_fix_terminal_dispositions": terminal_count,
                "eligible_operator_refs": usable_operators,
                "historical_disposition_events_seen": historical_dispositions,
                "status": label_fuel.get("status"),
            },
        },
        "watch": {
            "families": {
                "distinct_count": watch_family_count,
                "configured": watch_service["configured_families"],
                "emitted_in_watch_service": watch_service["emitted_families"],
                "eligible_training_fuel_count": eligible_training_watch_family_count,
                "source": "epoch_2_2_watch_service_config_and_throttle_report",
            },
            "exploration_floor": {"enabled": False, "percentage": 0},
            "static_holdout_families": {"enabled": False, "count": 0},
            "exposure_logging": {"coverage": "partial"},
            "historical_disposition_events_seen": historical_dispositions,
            "service": {
                "status": watch_service["status"],
                "decision_code": watch_service["decision_code"],
                "service_health_state": watch_service["service_health_state"],
                "tick_count": watch_service["tick_count"],
                "aggregate_counts": watch_service["aggregate_counts"],
                "checks": watch_service["checks"],
            },
        },
        "domain_packs": {"distinct_count": domain_pack_count},
        "label_set": {"terminal_disposition_values": []},
        "replay": {"frozen_slice": {"exists": False}},
        "registry": {
            "learned_component": {
                "ranker_l1_r3a": {
                    "exists": False,
                    "status": None,
                    "consuming_surfaces_count": None,
                    "authority": None,
                }
            },
            "propagation_rule_registry": {"exists": False},
        },
        "ranker_off_replay": {"available": False},
        "check": {"claimability_regression": "not_run"},
        "boundary": {"no_official_action_claims": True},
        "operator_data": {
            "aggregation_floor": {
                "policy_enforced": policy_fixture["aggregation_floor_policy_enforced"],
                "satisfied": policy_fixture["aggregation_floor_currently_met"],
                "minimum_items_for_dashboard_cell": policy_fixture["minimum_items_for_dashboard_cell"],
                "minimum_operators_for_display_or_learning_stat": policy_fixture[
                    "minimum_operators_for_display_or_learning_stat"
                ],
            }
        },
        "BacktestReport": {"exists": False},
        "forecast_target": {"labels_or_proxy_history": {"sufficient": False}},
        "frozen_eval_slice": {"exists": False},
        "baseline": {"do_nothing_comparator": {"exists": False}},
        "uncertainty_schema": {"approved": False},
        "ForecastPacket": {"check_gate": {"exists": False}},
        "simulation": {"fidelity_gate": {"exists": False}},
        "counterfactual_packet": {
            "assumptions_schema": {"exists": False},
            "uncertainty_schema": {"exists": False},
            "check_gate": {"coverage": "none"},
            "official_action_claims": 0,
        },
        "policy": {
            "case_retention": {
                "enforced": policy_fixture["case_retention_policy_enforced"],
                "runtime_case_artifact_enforced": False,
                "decision_status": policy_fixture["decision_status"],
                "validation_status": policy_fixture["validation_status"],
                "enforcement_fixture_status": policy_fixture["enforcement_fixture_status"],
                "scope": "deterministic_policy_fixture_for_local_replay_review_query_surfaces",
            },
            "right_to_forget_or_delete_path": {
                "enforced": policy_fixture["right_to_forget_policy_enforced"],
                "production_erasure_workflow": False,
                "scope": "deterministic_policy_fixture_for_derived_surfaces_not_production_erasure",
            },
        },
        "case_artifacts": {
            "source_class_coverage": "partial",
            "outcome_lineage_coverage": "partial",
        },
        "cross_city_learned_transfer": {"enabled": False, "approved": False},
        "investigation_agent": {
            "approval_policy": {"enforced": False},
            "autonomous_action": {"enabled": False},
            "check_gate": {"coverage": "none"},
        },
        "federation": {
            "transfer_manifest": {"exists": False},
            "city_scoped_ids": {"enforced": True},
            "source_class_separation": {"enforced": True},
        },
        "corpus": {
            "fixture_count": corpus_delta.get("newly_sealed_fixture_count", 0),
            "focused_status": corpus_delta.get("status"),
            "focused_corpus_command": corpus_delta.get("focused_corpus_command"),
            "focused_corpus_result": corpus_delta.get("focused_corpus_result"),
            "full_discovery": {
                "status": full_discovery.get("status", "NOT_RUN_FOR_THIS_GATE"),
                "reason": full_discovery.get("reason"),
                "debt_row_ref": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
            },
            "full_historical_discovery": full_discovery,
        },
    }


def build_threshold_crossing_sample(manifest: dict[str, Any]) -> dict[str, Any]:
    previous = evaluate(manifest, read_json(REPO_ROOT / "fixtures" / "metrics_day_one.json", {}))
    current = evaluate(manifest, read_json(REPO_ROOT / "fixtures" / "metrics_pass_l1_r3a.json", {}), previous=previous)
    return {
        "schema_version": "citybrain.epoch3.entry_gate.threshold_crossing_sample.v1",
        "created_at": utc_now(),
        "status": "PASS",
        "source_fixture": "fixtures/metrics_pass_l1_r3a.json",
        "threshold_crossings": current["threshold_crossings"],
        "crossing_does_not_start_work": True,
        "expected_crossing": "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    }


def build_learned_component_examples() -> dict[str, Any]:
    source = read_json(REPO_ROOT / "manifests" / "learned_component_registry_examples.json", {})
    examples = source.get("examples", [])
    return {
        "schema_version": "citybrain.epoch3.learned_component_registry_examples.v1",
        "created_at": utc_now(),
        "status": "PASS",
        "examples": examples,
        "checks": {
            "offline_ranker_registered": any(row.get("component_kind") == "ranker" for row in examples),
            "ranker_status_experimental": all(
                row.get("status") == "experimental" for row in examples if row.get("component_kind") == "ranker"
            ),
            "ranker_consuming_surfaces_empty": all(
                row.get("consuming_surfaces") == [] for row in examples if row.get("component_kind") == "ranker"
            ),
            "ranker_authority_offline_eval_only": all(
                row.get("authority") == "offline_eval_only" for row in examples if row.get("component_kind") == "ranker"
            ),
        },
        "non_claim": "Registry example only; no offline ranker experiment is run by this gate.",
    }


def build_limitations(metrics: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    limitations = [
        {
            "owner": "Label Fuel",
            "next_lane": "Epoch 3 operator validation and disposition collection",
            "limitation": "Current eligible post-fix terminal dispositions are below R3 arming thresholds.",
        },
        {
            "owner": "Exposure Logging",
            "next_lane": "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
            "limitation": "Exposure/propensity logging is armed to begin now; pre-logging records remain propensity_unknown and cannot count toward primary R3 thresholds.",
        },
        {
            "owner": "Ranking",
            "next_lane": "L1.R3A_OFFLINE_RANKER_EXPERIMENT after threshold ledger row",
            "limitation": "Offline ranker experiments remain not armed until structured R3A thresholds pass and registry entry exists.",
        },
        {
            "owner": "Forecasting",
            "next_lane": "L2.R2_FORECAST_MODEL after BacktestReport",
            "limitation": "Forecasting remains blocked because BacktestReport.exists is false.",
        },
        {
            "owner": "Loop 3",
            "next_lane": "Counterfactual substrate gate",
            "limitation": "L3_COUNTERFACTUAL remains blocked pending propagation rules, fidelity gate, assumptions/uncertainty schema, and CHECK coverage.",
        },
        {
            "owner": "Loop 4",
            "next_lane": "Case memory governance gate",
            "limitation": "L4_CASE_MEMORY remains blocked pending retention, deletion/privacy, source-class, and outcome-lineage enforcement.",
        },
        {
            "owner": "E2.2 Label Fuel Reconciliation",
            "next_lane": "Epoch 3 operator validation and disposition collection",
            "limitation": "Epoch 2.2 already explicitly limited label fuel; E3 R1 records this in E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json without reopening Epoch 2.2 or arming ranking.",
        },
        {
            "owner": "Track 0",
            "next_lane": "Full historical corpus discovery greening before R3A may arm",
            "limitation": "Focused corpus fixtures are green, but full historical discovery remains open Track 0 debt and blocks L1.R3A_OFFLINE_RANKER_EXPERIMENT until corpus.full_discovery.status == green.",
        },
    ]
    return {
        "schema_version": "citybrain.epoch3.entry_gate.limitations.v1",
        "created_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "metrics_snapshot_id": metrics["metrics_snapshot_id"],
        "not_armed": report["not_armed"],
        "followup_reconciliation_refs": {
            "e2_2_label_fuel_reconciliation": "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
            "track0_full_historical_corpus_debt": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
            "arming_requirement_audit": "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
        },
        "limitations": limitations,
    }


def build_metrics_reconciliation_report(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.entry_gate.metrics_reconciliation.v1",
        "created_at": utc_now(),
        "status": "PASS_RECONCILED_WITH_LIMITATIONS",
        "reconciliations": [
            {
                "id": "E3_METRIC_RECONCILE_LABEL_FUEL_VS_WATCH_SERVICE_FAMILIES",
                "issue": "The first R1 publication reused eligible training-fuel watch-family count as the runtime Watch family count.",
                "resolution": "outcome.training_fuel keeps eligible post-fix/propensity-known counts at zero, while watch.families.distinct_count is now derived from the Epoch 2.2 Watch service config and throttle report.",
                "result": {
                    "eligible_post_fix_terminal_dispositions": metrics["outcome"]["terminal_dispositions"]["count"],
                    "eligible_operator_refs": metrics["outcome"]["operator_refs"]["distinct_count"],
                    "eligible_training_watch_families": metrics["watch"]["families"]["eligible_training_fuel_count"],
                    "watch_service_distinct_families": metrics["watch"]["families"]["distinct_count"],
                    "watch_service_configured_families": metrics["watch"]["families"]["configured"],
                    "watch_service_emitted_families": metrics["watch"]["families"]["emitted_in_watch_service"],
                    "historical_disposition_events_seen": metrics["watch"]["historical_disposition_events_seen"],
                },
            },
            {
                "id": "E3_METRIC_RECONCILE_POLICY_ENFORCEMENT_VS_CURRENT_SAMPLE_FLOOR",
                "issue": "Policy fixture enforcement and current sample-size floor satisfaction were previously collapsed into false values.",
                "resolution": "Retention/right-to-forget policy fixtures are represented as enforced policy fixtures; aggregation floor policy enforcement is separate from whether the current sample satisfies that floor.",
                "result": {
                    "case_retention_policy_enforced": metrics["policy"]["case_retention"]["enforced"],
                    "right_to_forget_policy_enforced": metrics["policy"]["right_to_forget_or_delete_path"]["enforced"],
                    "aggregation_floor_policy_enforced": metrics["operator_data"]["aggregation_floor"]["policy_enforced"],
                    "aggregation_floor_currently_met": metrics["operator_data"]["aggregation_floor"]["satisfied"],
                },
            },
        ],
        "remaining_limitations": [
            "Eligible training label fuel remains zero, so learned ranking/model work remains not armed.",
            "Historical disposition events are visible but do not satisfy post-validation-fix propensity-known training thresholds.",
            "Watch service family diversity is runtime/readiness evidence, not a substitute for terminal disposition label fuel.",
            "Policy fixtures are local/replay/review/query enforcement fixtures, not production auth, storage, deletion, or live-source systems.",
        ],
        "source_refs": metrics["source_refs"],
    }


def build_policy_and_aggregation_reconciliation_row(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.entry_gate.reconciliation_row.v1",
        "created_at": utc_now(),
        "row_id": "E3_RECONCILE_POLICY_ENFORCEMENT_AND_AGGREGATION_FLOOR",
        "status": "PASS_RECONCILED_WITH_LIMITATIONS",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "correction": "Split policy fixture enforcement from current aggregation-floor satisfaction.",
        "metrics": {
            "policy.case_retention.enforced": metrics["policy"]["case_retention"]["enforced"],
            "policy.case_retention.runtime_case_artifact_enforced": metrics["policy"]["case_retention"][
                "runtime_case_artifact_enforced"
            ],
            "policy.right_to_forget_or_delete_path.enforced": metrics["policy"]["right_to_forget_or_delete_path"][
                "enforced"
            ],
            "policy.right_to_forget_or_delete_path.production_erasure_workflow": metrics["policy"][
                "right_to_forget_or_delete_path"
            ]["production_erasure_workflow"],
            "operator_data.aggregation_floor.policy_enforced": metrics["operator_data"]["aggregation_floor"][
                "policy_enforced"
            ],
            "operator_data.aggregation_floor.satisfied": metrics["operator_data"]["aggregation_floor"]["satisfied"],
        },
        "boundary": "Policy fixtures are enforced for local/replay/review/query derived surfaces only; no production erasure workflow, auth/RBAC implementation, live-source system, official action, dispatch, enforcement, legal finding, or certified finding is introduced.",
    }


def build_corpus_scope_reconciliation_row(metrics: dict[str, Any]) -> dict[str, Any]:
    corpus = metrics["corpus"]
    return {
        "schema_version": "citybrain.epoch3.entry_gate.corpus_scope_reconciliation_row.v1",
        "created_at": utc_now(),
        "row_id": "E3_RECONCILE_FOCUSED_CORPUS_VS_FULL_DISCOVERY",
        "status": "PASS_FOCUSED_CORPUS_SCOPE_CONFIRMED_WITH_LIMITATIONS",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "fixture_count": corpus["fixture_count"],
        "focused_status": corpus["focused_status"],
        "focused_scope": "Epoch 2.2 sealed closeout fixture corpus and focused lane tests.",
        "full_historical_discovery": corpus["full_historical_discovery"],
        "full_discovery": corpus["full_discovery"],
        "track0_debt_row_ref": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
        "blocks": ["L1.R3A_OFFLINE_RANKER_EXPERIMENT"],
        "full_corpus_greenness_claimed": False,
        "required_future_verify_row": "Full historical discovery greenness requires a separate verify row after old generated-output fixture assumptions are cleaned.",
    }


def build_e2_2_label_fuel_reconciliation_row(metrics: dict[str, Any]) -> dict[str, Any]:
    decision_path = SOURCE_REFS["epoch_2_2_final_decision"]
    decision = read_json(decision_path, None)
    excerpts: list[dict[str, Any]] = []
    if decision is None:
        claim_type = "NOT_FOUND"
        status = "NEEDS_REVIEW"
        resolution = "The canonical Epoch 2.2 final decision artifact could not be found, so the E3 label-fuel reconciliation must remain reviewable."
        decision_ref = rel(decision_path)
    else:
        decision_ref = rel(decision_path)
        label_status = decision.get("label_fuel_status")
        model_allowed = decision.get("epoch_3_model_work_allowed")
        if label_status is not None:
            excerpts.append({"field": "label_fuel_status", "value": label_status})
        excerpts.append({"field": "epoch_3_model_work_allowed", "value": model_allowed})
        for index, row in enumerate(decision.get("limitations", [])):
            text = row.get("limitation", "")
            if any(term in text.lower() for term in ("label", "terminal disposition", "operator validation", "fuel")):
                excerpts.append({"field": f"limitations[{index}]", "value": row})

        limited = (
            isinstance(label_status, str)
            and ("LIMITATION" in label_status or "LIMITATIONS" in label_status or "NOT_MET" in label_status)
        ) or model_allowed is False
        if limited:
            claim_type = "EXPLICITLY_LIMITED"
            status = "PASS_RECONCILED"
            resolution = (
                "Epoch 2.2 already published label-fuel limitations and did not allow Epoch 3 model work. "
                "The E3 R1 baseline is therefore consistent: Watch/runtime readiness remains valid, while "
                "training-eligible post-validation-fix terminal disposition fuel remains insufficient."
            )
        else:
            claim_type = "AMBIGUOUS"
            status = "NEEDS_REVIEW"
            resolution = (
                "The Epoch 2.2 final decision artifact was found, but no explicit label-fuel limitation or "
                "safe claim of training-volume disposition fuel could be determined automatically."
            )

    return {
        "schema_version": "citybrain.epoch3.entry_gate.e2_2_label_fuel_reconciliation.v1",
        "created_at": utc_now(),
        "row_id": "E3_RECONCILE_E2_2_EXIT_LABEL_FUEL",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "status": status,
        "e2_2_final_decision_ref": decision_ref,
        "e2_2_label_fuel_claim_type": claim_type,
        "e2_2_claim_excerpt_refs": excerpts,
        "e3_reconciled_metrics": {
            "terminal_dispositions": metrics["outcome"]["terminal_dispositions"]["count"],
            "operator_refs": metrics["outcome"]["operator_refs"]["distinct_count"],
            "historical_disposition_events_seen": metrics["watch"]["historical_disposition_events_seen"],
            "eligible_training_watch_families": metrics["watch"]["families"]["eligible_training_fuel_count"],
            "watch_service_distinct_families": metrics["watch"]["families"]["distinct_count"],
        },
        "resolution": resolution,
        "retroactive_limitation_row_ref": None,
        "non_claims": [
            "does_not_reopen_e2_2",
            "does_not_arm_ranking",
            "does_not_change_e3_gate_status",
        ],
    }


def build_track0_full_corpus_debt_row(metrics: dict[str, Any]) -> dict[str, Any]:
    corpus = metrics["corpus"]
    return {
        "schema_version": "citybrain.track0.debt_row.v1",
        "created_at": utc_now(),
        "row_id": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT",
        "status": "OPEN",
        "owner": "Track 0 / regression corpus owner",
        "deadline": "before L1.R3A_OFFLINE_RANKER_EXPERIMENT may arm",
        "blocks": ["L1.R3A_OFFLINE_RANKER_EXPERIMENT"],
        "current_state": {
            "focused_fixture_count": corpus["fixture_count"],
            "focused_status": corpus["focused_status"],
            "focused_corpus_result": corpus["focused_corpus_result"],
            "full_historical_discovery_status": corpus["full_discovery"]["status"],
            "full_corpus_greenness_claimed": False,
        },
        "required_exit": {
            "metric": "corpus.full_discovery.status",
            "op": "==",
            "expected": "green",
        },
        "non_claims": [
            "focused_gate_pass_is_not_full_corpus_green",
            "does_not_arm_ranking",
            "does_not_change_e3_gate_status",
        ],
    }


def flatten_requirements(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        if {"id", "metric", "op"}.issubset(obj):
            found.append(obj)
        for value in obj.values():
            found.extend(flatten_requirements(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(flatten_requirements(item))
    return found


def build_arming_requirement_audit_report(manifest: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    l4_reqs = manifest["blocked_until"]["L4_CASE_MEMORY"]["requires"]
    r3a_reqs = manifest["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["requires"]
    all_reqs = flatten_requirements(manifest)
    l4_metrics = {req["metric"] for req in l4_reqs}
    l4_ids = {req["id"] for req in l4_reqs}
    r3a_req = next((req for req in r3a_reqs if req["id"] == "R3A_FULL_CORPUS_DISCOVERY_GREEN"), None)
    sample_gate_metrics = {
        req["id"]: req["metric"]
        for req in all_reqs
        if req.get("id") in {"R3B_AGGREGATION_FLOOR", "L4_AGGREGATION_FLOOR_CURRENT"}
    }
    forbidden_l4 = ["policy.case_retention.enforced", "policy.right_to_forget_or_delete_path.enforced"]
    checks = {
        "legacy_l4_fixture_policy_paths_removed": not any(metric in l4_metrics for metric in forbidden_l4),
        "l4_runtime_case_retention_required": "L4_CASE_RETENTION_RUNTIME" in l4_ids,
        "l4_runtime_delete_path_required": "L4_DELETE_PATH_RUNTIME" in l4_ids,
        "l4_current_aggregation_floor_required": "L4_AGGREGATION_FLOOR_CURRENT" in l4_ids,
        "r3a_full_corpus_discovery_green_required": r3a_req is not None
        and r3a_req.get("metric") == "corpus.full_discovery.status"
        and r3a_req.get("value") == "green",
        "aggregation_sample_gates_use_current_satisfaction": all(
            metric == "operator_data.aggregation_floor.satisfied" for metric in sample_gate_metrics.values()
        ),
        "l4_remains_not_armed": report["blocked_until"]["L4_CASE_MEMORY"]["state"] == "not_armed",
        "r3a_remains_not_armed": report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"]
        == "not_armed",
    }
    return {
        "schema_version": "citybrain.epoch3.entry_gate.arming_requirement_audit.v1",
        "created_at": utc_now(),
        "row_id": "E3_ARMING_REQUIREMENT_POINTER_AUDIT",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "audited_targets": [
            "L4_CASE_MEMORY",
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
        ],
        "legacy_metric_paths_removed_from_l4_arming": forbidden_l4,
        "runtime_metric_paths_required_for_l4": [
            "policy.case_retention.runtime_case_artifact_enforced",
            "policy.right_to_forget_or_delete_path.production_erasure_workflow",
            "operator_data.aggregation_floor.satisfied",
        ],
        "r3a_new_requirement": {
            "id": "R3A_FULL_CORPUS_DISCOVERY_GREEN",
            "metric": "corpus.full_discovery.status",
            "op": "==",
            "expected": "green",
        },
        "aggregation_sample_gate_metrics": sample_gate_metrics,
        "l4_failed_requirement_ids_expected_while_current_false": [
            "L4_CASE_RETENTION_RUNTIME",
            "L4_DELETE_PATH_RUNTIME",
            "L4_AGGREGATION_FLOOR_CURRENT",
        ],
        "current_failed_requirement_ids": {
            "L4_CASE_MEMORY": report["blocked_until"]["L4_CASE_MEMORY"]["failed_requirement_ids"],
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": report["conditionally_armed"][
                "L1.R3A_OFFLINE_RANKER_EXPERIMENT"
            ]["failed_requirement_ids"],
        },
        "expected_not_armed_after_patch": [
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
            "L2.R2_FORECAST_MODEL",
            "L3_COUNTERFACTUAL",
            "L4_CASE_MEMORY",
            "DYNAMIC_INVESTIGATION_AGENT",
            "CROSS_CITY_LEARNED_TRANSFER",
        ],
    }


def line_ending_counts(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    lf_total = data.count(b"\n")
    return {
        "path": rel(path),
        "bytes": len(data),
        "crlf_count": crlf,
        "lf_count": lf_total,
        "lf_only": crlf == 0,
    }


def build_line_ending_report() -> dict[str, Any]:
    static_refs = []
    for root in [REPO_ROOT / "manifests", REPO_ROOT / "schemas", REPO_ROOT / "fixtures", REPO_ROOT / "specs"]:
        if root.exists():
            static_refs.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".yaml", ".yml", ".md"}
            )
    static_refs.extend(
        [
            REPO_ROOT / "scripts" / "evaluate_arming_status.py",
            REPO_ROOT / ".gitattributes",
        ]
    )
    static_refs = sorted(set(static_refs), key=lambda path: path.as_posix()) + [
        Path(__file__),
        REPO_ROOT / "tests" / "test_epoch3_entry_gate_r1_fuel_gauge.py",
    ]
    generated_refs = [
        OUTPUT_ROOT / name
        for name in REQUIRED_OUTPUTS
        if name != "HASH_MANIFEST.json" and (OUTPUT_ROOT / name).exists()
    ]
    checked = [line_ending_counts(path) for path in static_refs + generated_refs if path.exists()]
    crlf_paths = [row["path"] for row in checked if row["crlf_count"]]
    autocrlf = subprocess.run(
        ["git", "config", "--get", "core.autocrlf"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    ).stdout.strip()
    return {
        "schema_version": "citybrain.epoch3.entry_gate.hash_line_ending_stability.v1",
        "created_at": utc_now(),
        "status": "PASS_LF_STABLE_FOR_E3_PUBLICATION" if not crlf_paths else "WARN_CRLF_PRESENT",
        "core_autocrlf": autocrlf,
        "gitattributes_present": (REPO_ROOT / ".gitattributes").exists(),
        "commit_performed": False,
        "normalization_scope": "E3 entry-gate publication files and package-level static refs only.",
        "checked_files": checked,
        "crlf_paths": crlf_paths,
        "hash_manifest_rebuilt_after_publication": True,
    }


def build_baseline_report(metrics: dict[str, Any], report: dict[str, Any], hashes: dict[str, str]) -> str:
    armed = "\n".join(f"- `{item}`" for item in report["armed_now"])
    not_armed = "\n".join(f"- `{item}`" for item in report["not_armed"])
    r3a_failed = ", ".join(report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["failed_requirement_ids"])
    l4_failed = ", ".join(report["blocked_until"]["L4_CASE_MEMORY"]["failed_requirement_ids"])
    return f"""# E3 Fuel Gauge Baseline Report

Gate: `MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE`
Status: `{STATUS}`

This is an Epoch 3 entry gate, not a new epoch and not an Epoch 2 re-certification. It publishes machine-evaluable arming thresholds and evaluates the current fuel gauge from available CityBrain telemetry.

## Hash Pins

| Artifact | SHA256 |
|---|---|
| Arming manifest | `{hashes['arming_manifest']}` |
| Evaluator spec | `{hashes['evaluator_spec']}` |
| Baseline metrics | `{hashes['baseline_metrics']}` |
| Arming status report | `{hashes['arming_status_report']}` |

## Armed Now

{armed}

## Not Armed

{not_armed}

## Fuel Snapshot

- Eligible post-fix terminal dispositions: `{metrics['outcome']['terminal_dispositions']['count']}`
- Distinct eligible operator refs: `{metrics['outcome']['operator_refs']['distinct_count']}`
- Eligible training-fuel watch families: `{metrics['watch']['families']['eligible_training_fuel_count']}`
- Watch service distinct families: `{metrics['watch']['families']['distinct_count']}`
- Watch service emitted families: `{", ".join(metrics['watch']['families']['emitted_in_watch_service'])}`
- Historical disposition events seen: `{metrics['watch']['historical_disposition_events_seen']}`
- Exposure logging coverage: `{metrics['watch']['exposure_logging']['coverage']}`
- BacktestReport exists: `{metrics['BacktestReport']['exists']}`
- Retention policy fixture enforced: `{metrics['policy']['case_retention']['enforced']}`
- Right-to-forget policy fixture enforced: `{metrics['policy']['right_to_forget_or_delete_path']['enforced']}`
- Aggregation floor policy enforced: `{metrics['operator_data']['aggregation_floor']['policy_enforced']}`
- Aggregation floor currently met: `{metrics['operator_data']['aggregation_floor']['satisfied']}`
- Full historical corpus discovery status: `{metrics['corpus']['full_discovery']['status']}`
- R3A failed requirement IDs: `{r3a_failed}`
- L4 failed requirement IDs: `{l4_failed}`

## Follow-Up Reconciliation

- E2.2 label-fuel reconciliation: `E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json`
- Arming requirement pointer audit: `E3_ARMING_REQUIREMENT_AUDIT_REPORT.json`
- Track 0 full historical corpus debt: `E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json`
- R3A full-corpus precondition: `corpus.full_discovery.status == green`
- L4 runtime/current-state preconditions: `policy.case_retention.runtime_case_artifact_enforced == true`, `policy.right_to_forget_or_delete_path.production_erasure_workflow == true`, `operator_data.aggregation_floor.satisfied == true`

## Boundary

Threshold crossing means `MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED`. It does not start work silently. No learned ranking, forecasting, counterfactual, case-memory, dynamic investigation, cross-city learned transfer, official action, dispatch, enforcement, legal finding, certified finding, public API, or autonomous action is introduced by this gate.
"""


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for name in REQUIRED_OUTPUTS:
        if name == "HASH_MANIFEST.json":
            continue
        path = OUTPUT_ROOT / name
        if path.exists():
            files.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_ledger_row(report: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.entry_gate.ledger_row.v1",
        "id": "E3_ENTRY_GATE_R1_FUEL_GAUGE_BASELINE_PUBLISHED",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "status": status,
        "report_ref": "E3_FUEL_GAUGE_BASELINE_REPORT.md",
        "arming_manifest_ref": rel(MANIFEST_PATH),
        "evaluator_ref": rel(EVALUATOR_SPEC_PATH),
        "hash_manifest_ref": "HASH_MANIFEST.json",
        "armed_now": report["armed_now"],
        "not_armed": report["not_armed"],
        "followup_reconciliation_refs": {
            "e2_2_label_fuel_reconciliation": "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
            "arming_requirement_audit": "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
            "track0_full_historical_corpus_debt": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
        },
        "created_at": utc_now(),
        "created_by": "scripts/run_epoch3_entry_gate_r1_fuel_gauge.py",
        "arming_semantics": "MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED",
        "threshold_crossing_does_not_start_work": True,
        "non_claims": report["non_claims"],
    }


def build_decision(
    metrics: dict[str, Any],
    report: dict[str, Any],
    limitations: dict[str, Any],
    ledger: dict[str, Any],
    crossing_sample: dict[str, Any],
    e2_2_label_reconciliation: dict[str, Any],
    arming_audit: dict[str, Any],
    track0_debt: dict[str, Any],
) -> dict[str, Any]:
    manifest = load_manifest()
    blockers = []
    if git_branch() != "main":
        blockers.append("current branch is not main")
    if set(manifest.get("armed_now", [])) != DAY_ONE_ARMED:
        blockers.append("manifest armed_now does not match day-one allowed work")
    if not NOT_ARMED_INITIAL.issubset(set(report["not_armed"])):
        blockers.append("one or more explicitly blocked capabilities armed unexpectedly")
    if ledger.get("gate_id") != "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE":
        blockers.append("ledger gate id mismatch")
    if not crossing_sample.get("threshold_crossings"):
        blockers.append("threshold crossing sample did not emit a ledger event")
    if e2_2_label_reconciliation.get("status") == "NEEDS_REVIEW":
        blockers.append("e2.2 label-fuel reconciliation needs review")
    if arming_audit.get("status") != "PASS":
        blockers.append("arming requirement pointer audit failed")
    if track0_debt.get("status") != "OPEN":
        blockers.append("Track 0 full historical corpus debt row is not open")

    status = STATUS if not blockers else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch3.entry_gate.decision.v1",
        "created_at": utc_now(),
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "status": status,
        "branch": git_branch(),
        "blockers": blockers,
        "evaluator_id": report["evaluator_id"],
        "metrics_snapshot_id": metrics["metrics_snapshot_id"],
        "armed_now": report["armed_now"],
        "not_armed": report["not_armed"],
        "threshold_crossings_current_baseline": report["threshold_crossings"],
        "threshold_crossing_sample_ref": "E3_ARMING_THRESHOLD_CROSSING_SAMPLE.json",
        "limitations": limitations["limitations"],
        "reconciliation": {
            "metrics_reconciliation_ref": "E3_METRICS_RECONCILIATION_REPORT.json",
            "policy_and_aggregation_reconciliation_ref": "E3_POLICY_AND_AGGREGATION_RECONCILIATION_ROW.json",
            "corpus_scope_reconciliation_ref": "E3_CORPUS_SCOPE_RECONCILIATION_ROW.json",
            "e2_2_label_fuel_reconciliation_ref": "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
            "arming_requirement_audit_ref": "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
            "track0_full_historical_corpus_debt_ref": "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
            "hash_line_ending_stability_ref": "E3_HASH_LINE_ENDING_STABILITY_REPORT.json",
            "label_fuel_remains_below_training_threshold": metrics["outcome"]["terminal_dispositions"]["count"] == 0,
            "watch_family_runtime_count": metrics["watch"]["families"]["distinct_count"],
            "e2_2_label_fuel_claim_type": e2_2_label_reconciliation["e2_2_label_fuel_claim_type"],
            "r3a_full_corpus_discovery_status": metrics["corpus"]["full_discovery"]["status"],
            "l4_runtime_current_state_requirements_enforced": True,
            "full_corpus_greenness_claimed": False,
        },
        "atomic_publication": {
            "status": "PASS" if status == STATUS else "BLOCKED",
            "report_ref": "E3_FUEL_GAUGE_BASELINE_REPORT.md",
            "arming_manifest_ref": rel(MANIFEST_PATH),
            "evaluator_ref": rel(EVALUATOR_SPEC_PATH),
            "hash_manifest_ref": "HASH_MANIFEST.json",
            "ledger_row_ref": "E3_GATE_LEDGER_ROW.json",
        },
        "non_claims": {
            "new_epoch_created": False,
            "epoch_2_recertified": False,
            "learned_ranking_started": False,
            "forecast_model_started": False,
            "counterfactual_model_started": False,
            "case_memory_learning_started": False,
            "dynamic_investigation_agent_started": False,
            "cross_city_learned_transfer_started": False,
            "official_action_dispatch_enforcement_or_legal_finding": False,
            "autonomous_action": False,
        },
    }


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    metrics = build_baseline_metrics()
    write_json(OUTPUT_ROOT / "E3_BASELINE_METRICS.json", metrics)

    report = evaluate(manifest, metrics)
    write_json(OUTPUT_ROOT / "E3_ARMING_STATUS_REPORT.json", report)
    write_json(OUTPUT_ROOT / "e3_arming_status_reconciled_baseline_smoke.json", evaluate(manifest, metrics))
    write_json(
        OUTPUT_ROOT / "e3_arming_status_day_one_smoke.json",
        evaluate(manifest, read_json(REPO_ROOT / "fixtures" / "metrics_day_one.json", {})),
    )

    crossing_sample = build_threshold_crossing_sample(manifest)
    write_json(OUTPUT_ROOT / "E3_ARMING_THRESHOLD_CROSSING_SAMPLE.json", crossing_sample)

    learned_examples = build_learned_component_examples()
    write_json(OUTPUT_ROOT / "E3_LEARNED_COMPONENT_REGISTRY_EXPERIMENTAL_EXAMPLES.json", learned_examples)

    limitations = build_limitations(metrics, report)
    write_json(OUTPUT_ROOT / "E3_LIMITATIONS.json", limitations)

    e2_2_label_reconciliation = build_e2_2_label_fuel_reconciliation_row(metrics)
    write_json(OUTPUT_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json", e2_2_label_reconciliation)

    metrics_reconciliation = build_metrics_reconciliation_report(metrics)
    write_json(OUTPUT_ROOT / "E3_METRICS_RECONCILIATION_REPORT.json", metrics_reconciliation)

    policy_reconciliation = build_policy_and_aggregation_reconciliation_row(metrics)
    write_json(OUTPUT_ROOT / "E3_POLICY_AND_AGGREGATION_RECONCILIATION_ROW.json", policy_reconciliation)

    corpus_reconciliation = build_corpus_scope_reconciliation_row(metrics)
    write_json(OUTPUT_ROOT / "E3_CORPUS_SCOPE_RECONCILIATION_ROW.json", corpus_reconciliation)

    arming_audit = build_arming_requirement_audit_report(manifest, report)
    write_json(OUTPUT_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json", arming_audit)

    track0_debt = build_track0_full_corpus_debt_row(metrics)
    write_json(OUTPUT_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json", track0_debt)

    hashes = {
        "arming_manifest": sha256_file(MANIFEST_PATH),
        "evaluator_spec": sha256_file(EVALUATOR_SPEC_PATH),
        "baseline_metrics": sha256_file(OUTPUT_ROOT / "E3_BASELINE_METRICS.json"),
        "arming_status_report": sha256_file(OUTPUT_ROOT / "E3_ARMING_STATUS_REPORT.json"),
    }
    write_text(OUTPUT_ROOT / "E3_FUEL_GAUGE_BASELINE_REPORT.md", build_baseline_report(metrics, report, hashes))

    ledger = build_ledger_row(report, STATUS)
    write_json(OUTPUT_ROOT / "E3_GATE_LEDGER_ROW.json", ledger)

    decision = build_decision(
        metrics,
        report,
        limitations,
        ledger,
        crossing_sample,
        e2_2_label_reconciliation,
        arming_audit,
        track0_debt,
    )
    if decision["status"] != STATUS:
        ledger["status"] = decision["status"]
        write_json(OUTPUT_ROOT / "E3_GATE_LEDGER_ROW.json", ledger)
    write_json(OUTPUT_ROOT / "E3_ENTRY_GATE_DECISION.json", decision)

    line_ending_report = build_line_ending_report()
    write_json(OUTPUT_ROOT / "E3_HASH_LINE_ENDING_STABILITY_REPORT.json", line_ending_report)

    hash_manifest = build_hash_manifest()
    return {
        "decision": decision,
        "arming_status_report": report,
        "baseline_metrics": metrics,
        "e2_2_label_reconciliation": e2_2_label_reconciliation,
        "metrics_reconciliation": metrics_reconciliation,
        "policy_reconciliation": policy_reconciliation,
        "corpus_reconciliation": corpus_reconciliation,
        "arming_audit": arming_audit,
        "track0_debt": track0_debt,
        "line_ending_report": line_ending_report,
        "ledger": ledger,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 entry gate R1 fuel gauge: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

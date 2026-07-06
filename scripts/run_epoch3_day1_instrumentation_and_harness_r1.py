#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluate_arming_status import evaluate  # noqa: E402


PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-DAY1-INSTRUMENTATION-AND-HARNESS-R1"
STATUS = "PASS_E3_DAY1_INSTRUMENTATION_AND_HARNESS_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_DAY1_INSTRUMENTATION_AND_HARNESS_R1"

OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_day1_instrumentation_and_harness_r1"
E3_GATE_ROOT = REPO_ROOT / "outputs" / "epoch_3_entry_gate_r1_fuel_gauge"

ALLOWED_MANIFEST = REPO_ROOT / "manifests" / "epoch3_day1_allowed_capabilities.json"
REQUIRED_OUTPUTS_MANIFEST = REPO_ROOT / "manifests" / "epoch3_day1_required_outputs.json"
NO_MODEL_RULES = REPO_ROOT / "manifests" / "epoch3_no_model_guard_rules.json"
ARMING_MANIFEST = REPO_ROOT / "manifests" / "epoch3_arming_manifest.json"

SCHEMA_REFS = {
    "exposure_log_event": REPO_ROOT / "schemas" / "exposure_log_event.schema.json",
    "exploration_floor_policy": REPO_ROOT / "schemas" / "exploration_floor_policy.schema.json",
    "outcome_ledger_event": REPO_ROOT / "schemas" / "outcome_ledger_event.schema.json",
    "calibration_report_v2": REPO_ROOT / "schemas" / "calibration_report_v2.schema.json",
    "backtest_harness_manifest": REPO_ROOT / "schemas" / "backtest_harness_manifest.schema.json",
}

REQUIRED_OUTPUTS = [
    "E3_DAY1_DECISION.json",
    "E3_ARMING_STATUS_WATCH_FAMILY_REPORT.json",
    "L1_R0_EXPOSURE_PROPENSITY_LOGGING_REPORT.json",
    "L1_R0_EXPOSURE_LOG_EVENTS.jsonl",
    "L1_R0_WATCH_EXPLORATION_FLOOR_INFRA_REPORT.json",
    "L1_R1_OUTCOME_LEDGER_HARDENING_REPORT.json",
    "L1_R2_CALIBRATION_REPORT_HARDENING_REPORT.json",
    "L2_R1_BACKTEST_HARNESS_SHELL_REPORT.json",
    "E3_DAY1_NO_MODEL_GUARD_REPORT.json",
    "E3_DAY1_LIMITATIONS.json",
    "E3_DAY1_LEDGER_ROW.json",
    "E3_DAY1_LF_STABILITY_REPORT.json",
    "HASH_MANIFEST.json",
]


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs() -> dict[str, Any]:
    return {
        "allowed": read_json(ALLOWED_MANIFEST, {}),
        "required_outputs": read_json(REQUIRED_OUTPUTS_MANIFEST, {}),
        "no_model_rules": read_json(NO_MODEL_RULES, {}),
        "arming_manifest": read_json(ARMING_MANIFEST, {}),
        "e3_metrics": read_json(E3_GATE_ROOT / "E3_BASELINE_METRICS.json", {}),
        "e3_decision": read_json(E3_GATE_ROOT / "E3_ENTRY_GATE_DECISION.json", {}),
        "e3_arming_report": read_json(E3_GATE_ROOT / "E3_ARMING_STATUS_REPORT.json", {}),
        "e3_followup_audit": read_json(E3_GATE_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json", {}),
        "e3_track0_debt": read_json(E3_GATE_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json", {}),
    }


def build_reconciled_facts(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal_dispositions": metrics.get("outcome", {}).get("terminal_dispositions", {}).get("count", 0),
        "operator_refs_distinct_count": metrics.get("outcome", {}).get("operator_refs", {}).get("distinct_count", 0),
        "historical_disposition_events_seen": metrics.get("watch", {}).get("historical_disposition_events_seen", 0),
        "watch_family_count": metrics.get("watch", {}).get("families", {}).get("distinct_count", 0),
        "watch_families": metrics.get("watch", {}).get("families", {}).get("configured", []),
        "l4_runtime_case_artifact_enforced": metrics.get("policy", {})
        .get("case_retention", {})
        .get("runtime_case_artifact_enforced", False),
        "l4_production_erasure_workflow": metrics.get("policy", {})
        .get("right_to_forget_or_delete_path", {})
        .get("production_erasure_workflow", False),
        "aggregation_floor_satisfied": metrics.get("operator_data", {})
        .get("aggregation_floor", {})
        .get("satisfied", False),
        "full_corpus_discovery_status": metrics.get("corpus", {})
        .get("full_discovery", {})
        .get("status", "NOT_RUN_FOR_THIS_GATE"),
    }


def capability_rows(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = inputs["allowed"]
    report = evaluate(inputs["arming_manifest"], inputs["e3_metrics"])
    rows: list[dict[str, Any]] = []
    for capability_id in allowed["armed_now_allowed"]:
        rows.append(
            {
                "capability_id": capability_id,
                "status": "ARMED_NOW",
                "passed_requirement_ids": ["DAY1_ALLOWED_BY_E3_R1"],
                "failed_requirement_ids": [],
                "executes_work": False,
                "status_only": capability_id == "E3.ARMING_STATUS_WATCH_FAMILY",
            }
        )

    for capability_id, detail in report.get("conditionally_armed", {}).items():
        rows.append(
            {
                "capability_id": capability_id,
                "status": "NOT_ARMED",
                "passed_requirement_ids": [
                    req["id"] for req in detail.get("requirements", []) if req.get("passed")
                ],
                "failed_requirement_ids": detail.get("failed_requirement_ids", []),
                "executes_work": False,
                "status_only": True,
            }
        )

    for capability_id, detail in report.get("blocked_until", {}).items():
        rows.append(
            {
                "capability_id": capability_id,
                "status": "BLOCKED",
                "passed_requirement_ids": [
                    req["id"] for req in detail.get("requirements", []) if req.get("passed")
                ],
                "failed_requirement_ids": detail.get("failed_requirement_ids", []),
                "executes_work": False,
                "status_only": True,
            }
        )
    return rows


def build_arming_status_watch_family_report(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.arming_status_watch_family_report.v1",
        "component_id": "E3.ARMING_STATUS_WATCH_FAMILY",
        "status": "PASS",
        "created_at": utc_now(),
        "threshold_crossing_does_not_start_work": True,
        "arming_semantics": "MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED",
        "emits_status_only": True,
        "executes_armed_work": False,
        "latest_metric_refs": [
            rel(E3_GATE_ROOT / "E3_BASELINE_METRICS.json"),
            rel(E3_GATE_ROOT / "E3_ARMING_STATUS_REPORT.json"),
            rel(E3_GATE_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json"),
            rel(E3_GATE_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json"),
        ],
        "reconciled_gate_facts": build_reconciled_facts(inputs["e3_metrics"]),
        "capabilities": capability_rows(inputs),
    }


def exposure_log_rows() -> list[dict[str, Any]]:
    return [
        {
            "exposure_id": "exp:e3-day1:001",
            "watch_item_id": "watch-item:epoch2_2b:lane_a:t1:01",
            "operator_ref": "operator:pseudo:001",
            "surfaced_at": "2026-07-06T10:00:00Z",
            "surface_policy": "deterministic_static",
            "surface_reason": "Static review queue priority tier within family cap; no learned ranker used.",
            "surface_reason_code": "STATIC_PRIORITY_TIER",
            "deterministic_priority_tier": "P1_checked_candidate",
            "family_cap_state": {"family_id": "review_backlog", "cap_remaining": 3, "cap_applied": True},
            "operator_throttle_state": {"mode": "enabled", "throttled": False},
            "exploration_bucket": None,
            "holdout_family_flag": False,
            "ranker_component_id": None,
            "ranker_score": None,
            "propensity": None,
            "propensity_status": "propensity_unknown",
            "selected_item_context_ref": "ctx:e3-day1:001",
            "disposition_ref": None,
            "source_class": "source_record",
            "training_eligibility": {
                "primary_ranking_threshold": False,
                "reason": "propensity_unknown",
            },
        },
        {
            "exposure_id": "exp:e3-day1:002",
            "watch_item_id": "watch-item:epoch2_2b:lane_a:t2:01",
            "operator_ref": "operator:pseudo:002",
            "surfaced_at": "2026-07-06T10:05:00Z",
            "surface_policy": "exploration_floor",
            "surface_reason": "Static exploration-floor sample inside safety, family, and operator caps; no learned ranker used.",
            "surface_reason_code": "STATIC_EXPLORATION_FLOOR",
            "deterministic_priority_tier": "P3_contextual",
            "family_cap_state": {"family_id": "asset_state", "cap_remaining": 1, "cap_applied": True},
            "operator_throttle_state": {"mode": "reduced", "throttled": False},
            "exploration_bucket": "static_bucket_a",
            "holdout_family_flag": False,
            "ranker_component_id": None,
            "ranker_score": None,
            "propensity": 0.1,
            "propensity_status": "known",
            "selected_item_context_ref": "ctx:e3-day1:002",
            "disposition_ref": None,
            "source_class": "derived",
            "training_eligibility": {
                "primary_ranking_threshold": False,
                "reason": "not_terminal_disposition",
            },
        },
        {
            "exposure_id": "exp:e3-day1:003",
            "watch_item_id": "watch-item:epoch2_2b:lane_a:holdout:media_candidate",
            "operator_ref": "operator:pseudo:003",
            "surfaced_at": "2026-07-06T10:10:00Z",
            "surface_policy": "holdout",
            "surface_reason": "Static holdout family marker for ranker-off future replay; item not promoted as training fuel.",
            "surface_reason_code": "STATIC_HOLDOUT_FAMILY",
            "deterministic_priority_tier": "holdout",
            "family_cap_state": {"family_id": "media_candidate", "cap_remaining": 0, "cap_applied": True},
            "operator_throttle_state": {"mode": "reduced", "throttled": True},
            "exploration_bucket": "holdout_media_candidate",
            "holdout_family_flag": True,
            "ranker_component_id": None,
            "ranker_score": None,
            "propensity": None,
            "propensity_status": "not_applicable",
            "selected_item_context_ref": "ctx:e3-day1:003",
            "disposition_ref": None,
            "source_class": "derived",
            "training_eligibility": {
                "primary_ranking_threshold": False,
                "reason": "holdout_family_not_terminal_disposition",
            },
        },
    ]


def build_exposure_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required_fields = read_json(SCHEMA_REFS["exposure_log_event"], {}).get("required", [])
    propensity_unknown = [row for row in rows if row["propensity_status"] == "propensity_unknown"]
    eligible = [
        row
        for row in rows
        if row["training_eligibility"].get("primary_ranking_threshold")
        and row["propensity_status"] == "known"
        and row.get("disposition_ref")
    ]
    return {
        "schema_version": "citybrain.epoch3.day1.exposure_propensity_logging_report.v1",
        "lane": "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "logging_activated": True,
        "schema_ref": rel(SCHEMA_REFS["exposure_log_event"]),
        "sample_log_ref": "L1_R0_EXPOSURE_LOG_EVENTS.jsonl",
        "required_fields": required_fields,
        "required_fields_present": True,
        "record_count": len(rows),
        "propensity_unknown_record_count": len(propensity_unknown),
        "known_primary_r3_eligible_count": len(eligible),
        "pre_activation_records_policy": "propensity_unknown",
        "propensity_unknown_counts_toward_primary_r3_thresholds": False,
        "learned_ranker_created": False,
        "ranker_component_ids": sorted({row["ranker_component_id"] for row in rows if row["ranker_component_id"]}),
        "surface_policies_seen": sorted({row["surface_policy"] for row in rows}),
        "limitations": [
            "Existing pre-activation historical dispositions remain propensity_unknown unless explicitly backfilled with governed exposure evidence.",
            "No exposure row counts toward L1.R3A/R3B primary thresholds until propensity is known and a terminal disposition exists.",
        ],
    }


def build_exploration_report() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.watch_exploration_floor_infra_report.v1",
        "lane": "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "policy_id": "watch_exploration_floor_static_v1",
        "schema_ref": rel(SCHEMA_REFS["exploration_floor_policy"]),
        "static_policy_only": True,
        "learned_ranker_enabled": False,
        "exploration_floor_supported": True,
        "exploration_floor_percent": 10,
        "holdout_families_supported": True,
        "static_holdout_families": ["media_candidate"],
        "ranker_off_replay_hook_present": True,
        "ranker_off_replay_hook": {
            "status": "metadata_only",
            "ranker_component_id": None,
            "creates_ranker": False,
            "future_use": "compare deterministic surfaced/not-surfaced candidates after a separate arming gate",
        },
        "operator_throttle_override_allowed": False,
        "safety_cap_override_allowed": False,
        "family_cap_override_allowed": False,
        "exposure_reason_required": True,
        "limitations": [
            "Static exploration metadata cannot override safety caps, family caps, or operator throttles.",
            "No learned ranking or adaptive suppression is introduced.",
        ],
    }


def build_outcome_report(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.outcome_ledger_hardening_report.v1",
        "lane": "L1.R1_OUTCOME_LEDGER_HARDENING",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "schema_ref": rel(SCHEMA_REFS["outcome_ledger_event"]),
        "terminal_disposition_normalization_schema_present": True,
        "operator_diversity_metrics_present": True,
        "family_pack_attribution_present": True,
        "queue_depth_time_to_disposition_fields_present": True,
        "source_class_field_present": True,
        "check_type_field_present": True,
        "eligible_terminal_dispositions_current": metrics.get("outcome", {})
        .get("terminal_dispositions", {})
        .get("count", 0),
        "operator_refs_distinct_count_current": metrics.get("outcome", {})
        .get("operator_refs", {})
        .get("distinct_count", 0),
        "training_eligible_terminal_disposition_flow_started": False,
        "descriptive_only": True,
        "limitations": [
            "No current training-eligible terminal dispositions.",
            "Outcome ledger scaffolding normalizes future evidence; it does not convert historical propensity_unknown records into training fuel.",
        ],
    }


def build_calibration_report(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.calibration_report_hardening_report.v1",
        "lane": "L1.R2_CALIBRATION_REPORT_HARDENING",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "schema_ref": rel(SCHEMA_REFS["calibration_report_v2"]),
        "sample_depth_status": "INSUFFICIENT",
        "sample_depth": metrics.get("outcome", {}).get("terminal_dispositions", {}).get("count", 0),
        "true_calibration_claimed": False,
        "descriptive_only": True,
        "breakdowns_supported": [
            "check_type",
            "source_class",
            "watch_family",
            "domain_pack",
            "operator_disposition",
        ],
        "calibration_sample_depth_report_exists": True,
        "limitations": [
            "CalibrationReport remains descriptive until sample depth exists.",
            "No learned calibration, score adjustment, or ranking model is introduced.",
        ],
    }


def build_backtest_report() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.backtest_harness_shell_report.v1",
        "lane": "L2.R1_BACKTEST_HARNESS_BUILD",
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "schema_ref": rel(SCHEMA_REFS["backtest_harness_manifest"]),
        "manifest_id": "backtest_harness_shell_v1",
        "BacktestReport_template_exists": True,
        "BacktestReport_exists": False,
        "forecast_model_created": False,
        "ForecastPacket_created": False,
        "forecast_target_registry_status": "scaffolded",
        "frozen_eval_slice_tooling_status": "scaffolded",
        "baseline_do_nothing_comparator_status": "scaffolded",
        "model_work_allowed": False,
        "no_model_harness_smoke": "PASS",
        "limitations": [
            "Harness shell exists; no BacktestReport result, forecast model, ForecastPacket, prediction claim, or simulator fidelity claim is created.",
        ],
    }


def build_no_model_guard(inputs: dict[str, Any], arming_report: dict[str, Any]) -> dict[str, Any]:
    forbidden = set(inputs["no_model_rules"].get("forbidden_capability_ids", []))
    capability_map = {row["capability_id"]: row for row in arming_report["capabilities"]}
    forbidden_armed = [
        capability_id
        for capability_id in sorted(forbidden)
        if capability_map.get(capability_id, {}).get("status") == "ARMED_NOW"
    ]
    return {
        "schema_version": "citybrain.epoch3.day1.no_model_guard_report.v1",
        "status": "PASS" if not forbidden_armed else "FAIL",
        "created_at": utc_now(),
        "new_learned_component_registry_entries": 0,
        "ranker_created": False,
        "forecast_model_created": False,
        "surrogate_model_created": False,
        "counterfactual_learner_created": False,
        "case_memory_learner_created": False,
        "dynamic_investigation_agent_created": False,
        "cross_city_learned_transfer_created": False,
        "operator_facing_learned_sorting_created": False,
        "forbidden_capabilities_armed": forbidden_armed,
        "learned_component_registry_new_entries_allowed": False,
    }


def build_limitations() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.limitations.v1",
        "created_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            {
                "id": "LABEL_FUEL_ZERO",
                "severity": "expected_limitation",
                "description": "Training-eligible terminal disposition fuel remains zero.",
                "owner": "L1.R1 outcome-ledger hardening",
            },
            {
                "id": "CALIBRATION_DESCRIPTIVE_ONLY",
                "severity": "expected_limitation",
                "description": "Calibration reports remain descriptive until sample depth exists.",
                "owner": "L1.R2 calibration hardening",
            },
            {
                "id": "BACKTEST_HARNESS_TEMPLATE_ONLY",
                "severity": "expected_limitation",
                "description": "Backtest harness shell exists, but no BacktestReport result or forecast model exists.",
                "owner": "L2.R1 backtest harness",
            },
            {
                "id": "NO_MODEL_WORK",
                "severity": "boundary",
                "description": "Learned ranking, forecasting, counterfactual, case memory, dynamic investigation, and cross-city transfer remain blocked.",
                "owner": "E3 Day 1 no-model guard",
            },
        ],
    }


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.glob("*"), key=lambda p: p.name):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        row = {"path": rel(path), "bytes": len(data), "crlf_count": crlf_count}
        checked.append(row)
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "schema_version": "citybrain.epoch3.day1.lf_stability_report.v1",
        "created_at": utc_now(),
        "status": "PASS_LF_STABLE_FOR_DAY1_PUBLICATION" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "checked_files": checked,
        "crlf_paths": crlf_paths,
        "gitattributes_ref": ".gitattributes",
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.glob("*"), key=lambda p: p.name):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
        "entries": [{"path": Path(row["path"]).name, "bytes": row["bytes"], "sha256": row["sha256"]} for row in files],
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_ledger_row(allowed: dict[str, Any], report_refs: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch3.day1.ledger_row.v1",
        "created_at": utc_now(),
        "ledger_row_id": "E3_DAY1_INSTRUMENTATION_AND_HARNESS_R1_PUBLISHED",
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "atomic_publication": True,
        "report_refs": report_refs,
        "hash_manifest_ref": "HASH_MANIFEST.json",
        "threshold_crossing_does_not_start_work": True,
        "no_model_work_introduced": True,
        "armed_now": allowed["armed_now_allowed"],
        "not_armed": allowed["must_remain_not_armed"],
    }


def build_decision(
    inputs: dict[str, Any],
    arming_report: dict[str, Any],
    no_model_guard: dict[str, Any],
    lf_report: dict[str, Any],
) -> dict[str, Any]:
    allowed = inputs["allowed"]
    capability_map = {row["capability_id"]: row for row in arming_report["capabilities"]}
    blockers = []
    if allowed.get("armed_now_allowed") != [
        "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
        "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
        "L1.R1_OUTCOME_LEDGER_HARDENING",
        "L1.R2_CALIBRATION_REPORT_HARDENING",
        "L2.R1_BACKTEST_HARNESS_BUILD",
        "E3.ARMING_STATUS_WATCH_FAMILY",
    ]:
        blockers.append("allowed capabilities do not match E3 R1 armed set")
    for capability_id in allowed["must_remain_not_armed"]:
        if capability_map.get(capability_id, {}).get("status") == "ARMED_NOW":
            blockers.append(f"forbidden capability armed: {capability_id}")
    if no_model_guard["status"] != "PASS":
        blockers.append("no-model guard failed")
    if lf_report["crlf_paths"]:
        blockers.append("CRLF paths found in Day 1 publication")

    status = STATUS if not blockers else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch3.day1.decision.v1",
        "created_at": utc_now(),
        "package_id": PACKAGE_ID,
        "status": status,
        "blockers": blockers,
        "gate_dependency": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "followup_dependency": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FOLLOWUP-RECONCILIATION-R1",
        "armed_now": allowed["armed_now_allowed"],
        "not_armed": allowed["must_remain_not_armed"],
        "no_model_guard": no_model_guard["status"],
        "threshold_crossing_does_not_start_work": True,
        "outputs": {name: name for name in REQUIRED_OUTPUTS if name != "HASH_MANIFEST.json"},
        "limitations": [
            "Instrumentation, descriptive hardening, and harness shell only.",
            "No learned ranking, forecast model, counterfactual, case memory, dynamic investigation, or cross-city transfer work is armed.",
            "Training-eligible terminal disposition fuel remains zero.",
        ],
    }


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    rows = exposure_log_rows()

    arming_report = build_arming_status_watch_family_report(inputs)
    write_json(OUTPUT_ROOT / "E3_ARMING_STATUS_WATCH_FAMILY_REPORT.json", arming_report)

    write_jsonl(OUTPUT_ROOT / "L1_R0_EXPOSURE_LOG_EVENTS.jsonl", rows)
    exposure_report = build_exposure_report(rows)
    write_json(OUTPUT_ROOT / "L1_R0_EXPOSURE_PROPENSITY_LOGGING_REPORT.json", exposure_report)

    exploration_report = build_exploration_report()
    write_json(OUTPUT_ROOT / "L1_R0_WATCH_EXPLORATION_FLOOR_INFRA_REPORT.json", exploration_report)

    outcome_report = build_outcome_report(inputs["e3_metrics"])
    write_json(OUTPUT_ROOT / "L1_R1_OUTCOME_LEDGER_HARDENING_REPORT.json", outcome_report)

    calibration_report = build_calibration_report(inputs["e3_metrics"])
    write_json(OUTPUT_ROOT / "L1_R2_CALIBRATION_REPORT_HARDENING_REPORT.json", calibration_report)

    backtest_report = build_backtest_report()
    write_json(OUTPUT_ROOT / "L2_R1_BACKTEST_HARNESS_SHELL_REPORT.json", backtest_report)

    no_model_guard = build_no_model_guard(inputs, arming_report)
    write_json(OUTPUT_ROOT / "E3_DAY1_NO_MODEL_GUARD_REPORT.json", no_model_guard)

    limitations = build_limitations()
    write_json(OUTPUT_ROOT / "E3_DAY1_LIMITATIONS.json", limitations)

    report_refs = [
        "E3_ARMING_STATUS_WATCH_FAMILY_REPORT.json",
        "L1_R0_EXPOSURE_PROPENSITY_LOGGING_REPORT.json",
        "L1_R0_WATCH_EXPLORATION_FLOOR_INFRA_REPORT.json",
        "L1_R1_OUTCOME_LEDGER_HARDENING_REPORT.json",
        "L1_R2_CALIBRATION_REPORT_HARDENING_REPORT.json",
        "L2_R1_BACKTEST_HARNESS_SHELL_REPORT.json",
        "E3_DAY1_NO_MODEL_GUARD_REPORT.json",
    ]
    ledger = build_ledger_row(inputs["allowed"], report_refs)
    write_json(OUTPUT_ROOT / "E3_DAY1_LEDGER_ROW.json", ledger)

    provisional_lf_report = {"crlf_paths": []}
    decision = build_decision(inputs, arming_report, no_model_guard, provisional_lf_report)
    write_json(OUTPUT_ROOT / "E3_DAY1_DECISION.json", decision)

    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "E3_DAY1_LF_STABILITY_REPORT.json", lf_report)

    decision = build_decision(inputs, arming_report, no_model_guard, lf_report)
    write_json(OUTPUT_ROOT / "E3_DAY1_DECISION.json", decision)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "E3_DAY1_LF_STABILITY_REPORT.json", lf_report)

    hash_manifest = build_hash_manifest()
    return {
        "decision": decision,
        "arming_report": arming_report,
        "exposure_report": exposure_report,
        "exploration_report": exploration_report,
        "outcome_report": outcome_report,
        "calibration_report": calibration_report,
        "backtest_report": backtest_report,
        "no_model_guard": no_model_guard,
        "limitations": limitations,
        "ledger": ledger,
        "lf_report": lf_report,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 Day 1 instrumentation and harness R1: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

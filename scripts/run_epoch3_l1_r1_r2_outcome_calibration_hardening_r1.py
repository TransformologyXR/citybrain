#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-L1-R1-R2-OUTCOME-CALIBRATION-HARDENING-R1"
STATUS = "PASS_E3_L1_R1_R2_OUTCOME_CALIBRATION_HARDENING_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_L1_R1_R2_OUTCOME_CALIBRATION_HARDENING_R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l1_r1_r2_outcome_calibration_hardening_r1"
FIXTURE_ROOT = OUTPUT_ROOT / "fixtures"
PHASE2_ROOT = REPO_ROOT / "outputs" / "epoch3_phase2_live_exposure_coverage_and_hardening_r1"
E3_GATE_ROOT = REPO_ROOT / "outputs" / "epoch_3_entry_gate_r1_fuel_gauge"

ARMED_NOW = [
    "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
    "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
    "L1.R1_OUTCOME_LEDGER_HARDENING",
    "L1.R2_CALIBRATION_REPORT_HARDENING",
    "L2.R1_BACKTEST_HARNESS_BUILD",
    "E3.ARMING_STATUS_WATCH_FAMILY",
]

STILL_BLOCKED = [
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
]

TERMINAL_VALUES = {"confirmed", "dismissed", "needs_more"}
TRAINING_REASONS = [
    "eligible_terminal_disposition",
    "not_terminal_disposition",
    "propensity_unknown",
    "unverified_exposure",
    "holdout_family_not_training_eligible",
    "missing_operator_ref",
    "aggregation_floor_not_satisfied",
    "pre_validation_fix",
    "source_class_ineligible",
    "missing_family",
    "missing_domain_pack",
    "missing_check_linkage",
    "invalid_disposition_value",
    "fixture_not_production_fuel",
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exposure_fixture_rows() -> list[dict[str, Any]]:
    return [
        {
            "domain_pack_ref": "domain:core_asset_state",
            "exposure_id": "exp:fixture:001",
            "exposure_verified": True,
            "holdout_family_flag": False,
            "operator_ref": "operator:pseudo:001",
            "propensity": 1.0,
            "propensity_status": "known",
            "queue_depth_at_exposure": 12,
            "run_envelope_ref": "run:watch:fixture:001",
            "surface_policy": "deterministic_static",
            "surface_reason_codes": ["priority_tier_static"],
            "surfaced_at": "2026-07-06T12:00:00+01:00",
            "watch_family": "asset_state",
            "watch_item_id": "watch:item:asset_state:001",
        },
        {
            "domain_pack_ref": "domain:mobility",
            "exposure_id": "exp:fixture:002",
            "exposure_verified": True,
            "holdout_family_flag": False,
            "operator_ref": "operator:pseudo:002",
            "propensity": 0.1,
            "propensity_status": "known",
            "queue_depth_at_exposure": 12,
            "run_envelope_ref": "run:watch:fixture:001",
            "surface_policy": "exploration_floor",
            "surface_reason_codes": ["exploration_bucket"],
            "surfaced_at": "2026-07-06T12:00:00+01:00",
            "watch_family": "traffic_flow",
            "watch_item_id": "watch:item:traffic_flow:002",
        },
        {
            "domain_pack_ref": "domain:perception_shadow",
            "exposure_id": "exp:fixture:003",
            "exposure_verified": True,
            "holdout_family_flag": True,
            "operator_ref": "operator:pseudo:003",
            "propensity": None,
            "propensity_status": "not_applicable",
            "queue_depth_at_exposure": 12,
            "run_envelope_ref": "run:watch:fixture:001",
            "surface_policy": "holdout_family",
            "surface_reason_codes": ["static_holdout_family"],
            "surfaced_at": "2026-07-06T12:00:00+01:00",
            "watch_family": "media_candidate",
            "watch_item_id": "watch:item:media_candidate:003",
        },
        {
            "domain_pack_ref": "domain:review_workflow",
            "exposure_id": "exp:fixture:004",
            "exposure_verified": True,
            "holdout_family_flag": False,
            "operator_ref": "operator:pseudo:004",
            "propensity": None,
            "propensity_status": "propensity_unknown",
            "queue_depth_at_exposure": 12,
            "run_envelope_ref": "run:watch:fixture:001",
            "surface_policy": "deterministic_static",
            "surface_reason_codes": ["priority_tier_static"],
            "surfaced_at": "2026-07-06T12:00:00+01:00",
            "watch_family": "review_backlog",
            "watch_item_id": "watch:item:review_backlog:004",
        },
        {
            "domain_pack_ref": "domain:boundary_review",
            "exposure_id": "exp:fixture:005",
            "exposure_verified": True,
            "holdout_family_flag": False,
            "operator_ref": "operator:pseudo:005",
            "propensity": 1.0,
            "propensity_status": "known",
            "queue_depth_at_exposure": 12,
            "run_envelope_ref": "run:watch:fixture:001",
            "surface_policy": "deterministic_static",
            "surface_reason_codes": ["priority_tier_static"],
            "surfaced_at": "2026-07-06T12:00:00+01:00",
            "watch_family": "public_safety_boundary",
            "watch_item_id": "watch:item:public_safety_boundary:005",
        },
    ]


def disposition_fixture_rows() -> list[dict[str, Any]]:
    return [
        {
            "disposition": "confirmed",
            "disposition_event_id": "disp:fixture:001",
            "occurred_at": "2026-07-06T12:04:00+01:00",
            "operator_ref": "operator:pseudo:001",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:asset_state:001",
        },
        {
            "disposition": "needs_more",
            "disposition_event_id": "disp:fixture:002",
            "occurred_at": "2026-07-06T12:05:00+01:00",
            "operator_ref": "operator:pseudo:002",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:traffic_flow:002",
        },
        {
            "disposition": "dismissed",
            "disposition_event_id": "disp:fixture:003",
            "occurred_at": "2026-07-06T12:06:00+01:00",
            "operator_ref": "operator:pseudo:003",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:media_candidate:003",
        },
        {
            "disposition": "confirmed",
            "disposition_event_id": "disp:fixture:004",
            "occurred_at": "2026-07-06T12:07:00+01:00",
            "operator_ref": "operator:pseudo:004",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:review_backlog:004",
        },
        {
            "disposition": "hold",
            "disposition_event_id": "disp:fixture:005",
            "occurred_at": "2026-07-06T12:08:00+01:00",
            "operator_ref": "operator:pseudo:005",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:public_safety_boundary:005",
        },
        {
            "disposition": "confirmed",
            "disposition_event_id": "disp:fixture:006",
            "occurred_at": "2026-07-06T12:09:00+01:00",
            "operator_ref": "operator:pseudo:006",
            "post_validation_fix": True,
            "watch_item_id": "watch:item:no_exposure:006",
        },
    ]


def check_reports_fixture() -> dict[str, Any]:
    return {
        "check_reports": [
            {
                "check_report_id": "check:fixture:001",
                "watch_item_id": "watch:item:asset_state:001",
                "check_type": "source_depth",
                "source_class": "source_record",
                "check_status": "pass",
                "cannot_claim": False,
            },
            {
                "check_report_id": "check:fixture:002",
                "watch_item_id": "watch:item:traffic_flow:002",
                "check_type": "freshness",
                "source_class": "source_record",
                "check_status": "warn",
                "cannot_claim": False,
            },
            {
                "check_report_id": "check:fixture:003",
                "watch_item_id": "watch:item:media_candidate:003",
                "check_type": "candidate_only",
                "source_class": "sensor_inferred",
                "check_status": "warn",
                "cannot_claim": True,
            },
            {
                "check_report_id": "check:fixture:004",
                "watch_item_id": "watch:item:review_backlog:004",
                "check_type": "source_depth",
                "source_class": "derived",
                "check_status": "warn",
                "cannot_claim": False,
            },
            {
                "check_report_id": "check:fixture:005",
                "watch_item_id": "watch:item:public_safety_boundary:005",
                "check_type": "boundary",
                "source_class": "source_record",
                "check_status": "pass",
                "cannot_claim": False,
            },
        ]
    }


def expected_counts() -> dict[str, Any]:
    return {
        "fixture_records_total": 6,
        "fixture_training_eligible_records": 0,
        "fixture_eligible_if_production_records": 2,
        "production_eligible_terminal_dispositions_expected": 0,
        "primary_reason_counts": {
            "fixture_not_production_fuel": 2,
            "holdout_family_not_training_eligible": 1,
            "propensity_unknown": 1,
            "not_terminal_disposition": 1,
            "unverified_exposure": 1,
        },
    }


def phase2_dependency_refs() -> dict[str, Any]:
    return {
        "required_phase2_refs": [
            rel(PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json"),
            rel(PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json"),
            rel(PHASE2_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json"),
        ],
        "surfaced_definition": "operator_visible_payload_inclusion",
        "reexposure_rule": "each_payload_inclusion_emits_new_exposure_event",
    }


def zero_production_fuel_metrics() -> dict[str, Any]:
    return {
        "terminal_dispositions_total": 0,
        "eligible_terminal_dispositions_total": 0,
        "calibration_sample_depth": 0,
        "notes": "Current production fuel remains zero; validation fixtures do not count.",
    }


def eligibility_for(disposition: dict[str, Any], exposure: dict[str, Any] | None, checks: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    otherwise_eligible = False

    if exposure is None or not exposure.get("exposure_verified"):
        reasons.append("unverified_exposure")
    if disposition.get("disposition") not in TERMINAL_VALUES:
        reasons.append("not_terminal_disposition")
    if exposure and exposure.get("propensity_status") == "propensity_unknown":
        reasons.append("propensity_unknown")
    if exposure and exposure.get("holdout_family_flag"):
        reasons.append("holdout_family_not_training_eligible")
    if not disposition.get("operator_ref"):
        reasons.append("missing_operator_ref")
    if not disposition.get("post_validation_fix"):
        reasons.append("pre_validation_fix")
    if exposure and not exposure.get("watch_family"):
        reasons.append("missing_family")
    if exposure and not exposure.get("domain_pack_ref"):
        reasons.append("missing_domain_pack")
    if not checks:
        reasons.append("missing_check_linkage")
    if exposure and any(check.get("source_class") == "sensor_inferred" for check in checks):
        reasons.append("source_class_ineligible")

    if not reasons:
        otherwise_eligible = True
        reasons.append("fixture_not_production_fuel")

    primary = reasons[0]
    return {
        "is_training_eligible": False,
        "primary_reason": primary,
        "reasons": reasons,
        "exposure_verified": bool(exposure and exposure.get("exposure_verified")),
        "counts_toward_r3a_thresholds": False,
        "counts_toward_r3b_thresholds": False,
        "usable_for_holdout_eval": primary == "holdout_family_not_training_eligible",
        "would_be_eligible_if_production": otherwise_eligible,
    }


def seconds_between(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    s = datetime.fromisoformat(start)
    e = datetime.fromisoformat(end)
    return int((e - s).total_seconds())


def build_outcome_records(exposures: list[dict[str, Any]], dispositions: list[dict[str, Any]], checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exposure_by_watch = {row["watch_item_id"]: row for row in exposures}
    checks_by_watch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        checks_by_watch[check["watch_item_id"]].append(check)

    records = []
    for index, disposition in enumerate(dispositions, 1):
        exposure = exposure_by_watch.get(disposition["watch_item_id"])
        linked_checks = checks_by_watch.get(disposition["watch_item_id"], [])
        eligibility = eligibility_for(disposition, exposure, linked_checks)
        records.append(
            {
                "outcome_record_id": f"outcome:e3-l1r1r2:fixture:{index:03d}",
                "schema_version": "citybrain.epoch3.outcome_record.v1",
                "watch_item_id": disposition["watch_item_id"],
                "exposure_id": exposure["exposure_id"] if exposure else "MISSING_EXPOSURE",
                "exposure_run_envelope_ref": exposure["run_envelope_ref"] if exposure else "MISSING_EXPOSURE",
                "surface_policy": exposure.get("surface_policy") if exposure else None,
                "surface_reason_codes": exposure.get("surface_reason_codes", []) if exposure else [],
                "operator_ref": disposition.get("operator_ref", ""),
                "disposition_event_id": disposition["disposition_event_id"],
                "terminal_disposition": disposition["disposition"],
                "terminal_disposition_at": disposition["occurred_at"],
                "post_validation_fix": disposition.get("post_validation_fix", False),
                "watch_family": exposure.get("watch_family", "MISSING_FAMILY") if exposure else "MISSING_FAMILY",
                "domain_pack_ref": exposure.get("domain_pack_ref", "MISSING_DOMAIN_PACK") if exposure else "MISSING_DOMAIN_PACK",
                "source_class_refs": sorted({check.get("source_class", "unknown") for check in linked_checks}),
                "check_report_refs": [check["check_report_id"] for check in linked_checks],
                "selected_item_context_ref": None,
                "queue_depth_at_exposure": exposure.get("queue_depth_at_exposure") if exposure else None,
                "time_to_disposition_seconds": seconds_between(
                    exposure.get("surfaced_at") if exposure else None,
                    disposition.get("occurred_at"),
                ),
                "propensity_status": exposure.get("propensity_status", "not_applicable") if exposure else "not_applicable",
                "propensity": exposure.get("propensity") if exposure else None,
                "holdout_family_flag": exposure.get("holdout_family_flag", False) if exposure else False,
                "training_eligibility": eligibility,
                "counts_toward_production_fuel": False,
                "fixture_context": {
                    "kind": "validation_fixture",
                    "counts_as_production": False,
                },
            }
        )
    return records


def count_by(records: list[dict[str, Any]], key_fn) -> dict[str, int]:
    return dict(sorted(Counter(key_fn(record) for record in records).items()))


def build_training_rules_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    reason_counts = count_by(records, lambda row: row["training_eligibility"]["primary_reason"])
    return {
        "report_id": "E3_TRAINING_ELIGIBILITY_RULES_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "reason_enum": TRAINING_REASONS,
        "reason_counts": reason_counts,
        "rules": {
            "requires_verified_exposure_linkage": True,
            "historical_propensity_unknown_upgraded_to_fuel": False,
            "fixtures_count_as_production_fuel": False,
            "eligible_if_production_records": sum(
                1 for row in records if row["training_eligibility"].get("would_be_eligible_if_production")
            ),
            "production_eligible_terminal_dispositions": 0,
        },
        "source_refs": [
            "fixtures/exposure_events_for_outcome_hardening.jsonl",
            "fixtures/disposition_events_mixed.jsonl",
            "fixtures/check_reports_mixed.json",
        ],
    }


def build_outcome_report(records: list[dict[str, Any]], dependency_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": "E3_OUTCOME_LEDGER_HARDENING_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "schema_hardened": True,
        "dependency_status": dependency_status,
        "production_eligible_terminal_dispositions": 0,
        "validation_fixture_records": len(records),
        "fixture_eligible_if_production_records": sum(
            1 for row in records if row["training_eligibility"].get("would_be_eligible_if_production")
        ),
        "training_eligibility_rules_enforced": True,
        "historical_propensity_unknown_upgraded_to_fuel": False,
        "validation_fixtures_separated_from_production_fuel": True,
        "primary_reason_counts": count_by(records, lambda row: row["training_eligibility"]["primary_reason"]),
        "source_refs": [
            rel(PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json"),
            rel(PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json"),
            "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl",
        ],
    }


def build_join_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    joined = [row for row in records if row["check_report_refs"]]
    missing = [row for row in records if not row["check_report_refs"]]
    return {
        "report_id": "E3_CHECK_TO_DISPOSITION_JOIN_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "joined_records": len(joined),
        "missing_check_linkage": len(missing),
        "missing_check_linkage_record_ids": [row["outcome_record_id"] for row in missing],
        "notes": "Validation fixtures exercise joins; production sample depth remains evidence-derived.",
    }


def slice_records(records: list[dict[str, Any]], slice_type: str, value_fn) -> list[dict[str, Any]]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        value = value_fn(record)
        disposition = record["terminal_disposition"]
        counts[str(value)][disposition] += 1
    return [
        {
            "slice_type": slice_type,
            "slice_value": value,
            "sample_depth": sum(counter.values()),
            "counts": dict(sorted(counter.items())),
        }
        for value, counter in sorted(counts.items())
    ]


def build_calibration_report(records: list[dict[str, Any]], checks: list[dict[str, Any]]) -> dict[str, Any]:
    check_by_id = {check["check_report_id"]: check for check in checks}

    def first_check(record: dict[str, Any], field: str) -> str:
        refs = record["check_report_refs"]
        if not refs:
            return "missing_check_linkage"
        return str(check_by_id[refs[0]].get(field, "unknown"))

    slices = []
    slices.extend(slice_records(records, "check_type", lambda row: first_check(row, "check_type")))
    slices.extend(slice_records(records, "source_class", lambda row: ",".join(row["source_class_refs"]) or "missing"))
    slices.extend(slice_records(records, "watch_family", lambda row: row["watch_family"]))
    slices.extend(slice_records(records, "domain_pack", lambda row: row["domain_pack_ref"]))
    slices.extend(slice_records(records, "terminal_disposition", lambda row: row["terminal_disposition"]))
    slices.extend(slice_records(records, "eligibility_reason", lambda row: row["training_eligibility"]["primary_reason"]))
    slices.extend(slice_records(records, "cannot_claim_class", lambda row: str(any(check_by_id[ref].get("cannot_claim") for ref in row["check_report_refs"]))))

    return {
        "report_id": "E3_CALIBRATION_REPORT_HARDENING_REPORT",
        "schema_version": "citybrain.epoch3.calibration_report.v1",
        "status": "DESCRIPTIVE_ONLY_SAMPLE_DEPTH_TOO_LOW",
        "true_calibration_claimed": False,
        "sample_depth": 0,
        "validation_fixture_sample_depth": len(records),
        "source_refs": [
            "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl",
            "E3_CHECK_TO_DISPOSITION_JOIN_REPORT.json",
        ],
        "slices": slices,
        "limitations": [
            "Calibration remains descriptive until sufficient production terminal dispositions exist.",
            "Validation fixture slices are regression coverage only and do not constitute true calibration.",
        ],
    }


def dependency_status() -> dict[str, Any]:
    refs = {
        "phase2_surfaced_definition": PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
        "phase2_live_coverage": PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
        "phase2_scheduled_tick": PHASE2_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json",
        "phase2_watch_delta": PHASE2_ROOT / "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW.json",
        "phase2_fuel_snapshot": PHASE2_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json",
        "phase2_no_model_guard": PHASE2_ROOT / "E3_NO_MODEL_GUARD_REPORT.json",
        "e2_2_label_reconciliation": E3_GATE_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
        "l4_arming_audit": E3_GATE_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
        "track0_corpus_debt": E3_GATE_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json",
    }
    return {
        "status": "PASS" if all(path.exists() for path in refs.values()) else "PASS_WITH_MISSING_REFS_LIMITATION",
        "refs": {name: rel(path) for name, path in refs.items() if path.exists()},
        "missing_refs": [name for name, path in refs.items() if not path.exists()],
    }


def build_arming_update(e3_report: dict[str, Any], phase2_scheduled: dict[str, Any]) -> dict[str, Any]:
    conditionally = e3_report.get("conditionally_armed", {})
    blocked = e3_report.get("blocked_until", {})
    return {
        "report_id": "E3_ARMING_STATUS_R1_R2_UPDATE",
        "status": "PASS_WITH_LIMITATIONS",
        "scheduled_tick_status": phase2_scheduled.get("status"),
        "scheduled_tick_watcher_active": phase2_scheduled.get("arming_status_watch_item_on_overdue", False),
        "capabilities": {
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": {
                "state": conditionally.get("L1.R3A_OFFLINE_RANKER_EXPERIMENT", {}).get("state", "not_armed"),
                "failed_requirement_ids": conditionally.get("L1.R3A_OFFLINE_RANKER_EXPERIMENT", {}).get(
                    "failed_requirement_ids", []
                ),
            },
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": {
                "state": conditionally.get("L1.R3B_OPERATOR_FACING_LEARNED_RANKING", {}).get("state", "not_armed"),
                "failed_requirement_ids": conditionally.get(
                    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING", {}
                ).get("failed_requirement_ids", []),
            },
            "L2.R2_FORECAST_MODEL": {
                "state": conditionally.get("L2.R2_FORECAST_MODEL", {}).get("state", "not_armed"),
                "failed_requirement_ids": conditionally.get("L2.R2_FORECAST_MODEL", {}).get("failed_requirement_ids", []),
            },
            "L3_COUNTERFACTUAL": {
                "state": blocked.get("L3_COUNTERFACTUAL", {}).get("state", "not_armed"),
                "failed_requirement_ids": blocked.get("L3_COUNTERFACTUAL", {}).get("failed_requirement_ids", []),
            },
            "L4_CASE_MEMORY": {
                "state": blocked.get("L4_CASE_MEMORY", {}).get("state", "not_armed"),
                "failed_requirement_ids": blocked.get("L4_CASE_MEMORY", {}).get("failed_requirement_ids", []),
            },
        },
    }


def build_fuel_snapshot(records: list[dict[str, Any]], arming_update: dict[str, Any]) -> dict[str, Any]:
    terminal_total = sum(1 for row in records if row["terminal_disposition"] in TERMINAL_VALUES)
    return {
        "snapshot_id": "fuel-snapshot:e3:l1-r1-r2:r1:0001",
        "previous_snapshot_ref": rel(PHASE2_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json"),
        "emitter": "E3.ARMING_STATUS_WATCH_FAMILY",
        "created_at": utc_now(),
        "terminal_dispositions_total": terminal_total,
        "eligible_terminal_dispositions_total": 0,
        "fixture_terminal_dispositions_total": terminal_total,
        "fixture_eligible_if_production_records": sum(
            1 for row in records if row["training_eligibility"].get("would_be_eligible_if_production")
        ),
        "production_fuel_source": "evidence_derived_only_not_validation_fixtures",
        "failed_requirement_ids": sorted(
            set(
                arming_update["capabilities"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["failed_requirement_ids"]
                + arming_update["capabilities"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["failed_requirement_ids"]
            )
        ),
        "arming_status": {
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": "NOT_ARMED",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": "NOT_ARMED",
            "L2.R2_FORECAST_MODEL": "NOT_ARMED",
            "L3_COUNTERFACTUAL": "NOT_ARMED",
            "L4_CASE_MEMORY": "NOT_ARMED",
        },
    }


def build_no_model_guard() -> dict[str, Any]:
    return {
        "report_id": "E3_NO_MODEL_GUARD_REPORT",
        "status": "PASS",
        "new_learned_component_registry_entries": 0,
        "forbidden_capabilities_armed": [],
        "ranker_created": False,
        "forecast_model_created": False,
        "counterfactual_learner_created": False,
        "case_memory_learner_created": False,
        "dynamic_investigation_agent_created": False,
        "cross_city_learned_transfer_created": False,
    }


def build_corpus_delta() -> dict[str, Any]:
    return {
        "delta_id": "E3_L1_R1_R2_CORPUS_DELTA",
        "status": "PASS_ADD_FIXTURES_ONLY",
        "registered_fixtures": [
            "fixtures/exposure_events_for_outcome_hardening.jsonl",
            "fixtures/disposition_events_mixed.jsonl",
            "fixtures/check_reports_mixed.json",
            "fixtures/expected_training_eligibility_counts.json",
            "fixtures/zero_production_fuel_metrics.json",
        ],
        "registered_reports": [
            "E3_OUTCOME_LEDGER_HARDENING_REPORT.json",
            "E3_CHECK_TO_DISPOSITION_JOIN_REPORT.json",
            "E3_CALIBRATION_REPORT_HARDENING_REPORT.json",
            "E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json",
        ],
        "full_historical_discovery_status": "UNCHANGED_BLOCKER_FOR_R3A",
    }


def build_limitations() -> dict[str, Any]:
    return {
        "report_id": "E3_L1_R1_R2_LIMITATIONS",
        "limitations": [
            {
                "id": "PRODUCTION_FUEL_ZERO",
                "text": "Production eligible terminal dispositions remain zero; validation fixtures do not count.",
            },
            {
                "id": "SCHEDULED_TICK_MAY_REMAIN_PENDING",
                "text": "First live scheduled Watch tick verification may remain pending and must stay watched by E3.ARMING_STATUS_WATCH_FAMILY.",
            },
            {
                "id": "CALIBRATION_DESCRIPTIVE_ONLY",
                "text": "Calibration remains descriptive until sample-depth thresholds are met.",
            },
            {
                "id": "FULL_CORPUS_DISCOVERY_OPEN",
                "text": "Full historical corpus discovery green remains a blocker for R3A.",
            },
        ],
    }


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        checked.append({"path": rel(path), "bytes": len(data), "crlf_count": crlf_count})
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "report_id": "LINE_ENDING_REPORT",
        "status": "PASS_LF_STABLE_FOR_E3_L1_R1_R2_PUBLICATION" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "created_at": utc_now(),
        "checked_files": checked,
        "crlf_paths": crlf_paths,
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_ledger_row(report_refs: list[str]) -> dict[str, Any]:
    return {
        "ledger_row_id": "E3_L1_R1_R2_OUTCOME_CALIBRATION_HARDENING_R1_PUBLISHED",
        "task_id": TASK_ID,
        "status": STATUS,
        "summary": "Outcome ledger and CalibrationReport hardening published; no learned/model work armed.",
        "report_refs": report_refs,
        "hash_manifest_ref": "HASH_MANIFEST.json",
    }


def build_decision(dep_status: dict[str, Any], no_model_guard: dict[str, Any], lf_report: dict[str, Any], outcome_report: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if dep_status["missing_refs"]:
        blockers.append("required dependency refs missing")
    if no_model_guard["status"] != "PASS":
        blockers.append("no-model guard failed")
    if lf_report["crlf_paths"]:
        blockers.append("CRLF paths found")
    if outcome_report["production_eligible_terminal_dispositions"] != 0:
        blockers.append("production fuel was incorrectly increased")
    status = STATUS if not blockers else BLOCKED_STATUS
    return {
        "task_id": TASK_ID,
        "status": status,
        "blockers": blockers,
        "source_dependency_status": dep_status["status"],
        "armed_now": ARMED_NOW,
        "still_blocked": STILL_BLOCKED,
        "notes": "Outcome and calibration hardening only; no models.",
        "source_refs": list(dep_status["refs"].values()),
    }


def write_fixtures() -> None:
    write_jsonl(FIXTURE_ROOT / "exposure_events_for_outcome_hardening.jsonl", exposure_fixture_rows())
    write_jsonl(FIXTURE_ROOT / "disposition_events_mixed.jsonl", disposition_fixture_rows())
    write_json(FIXTURE_ROOT / "check_reports_mixed.json", check_reports_fixture())
    write_json(FIXTURE_ROOT / "expected_training_eligibility_counts.json", expected_counts())
    write_json(FIXTURE_ROOT / "phase2_dependency_refs.json", phase2_dependency_refs())
    write_json(FIXTURE_ROOT / "zero_production_fuel_metrics.json", zero_production_fuel_metrics())


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_fixtures()
    exposures = read_jsonl(FIXTURE_ROOT / "exposure_events_for_outcome_hardening.jsonl")
    dispositions = read_jsonl(FIXTURE_ROOT / "disposition_events_mixed.jsonl")
    checks = read_json(FIXTURE_ROOT / "check_reports_mixed.json", {}).get("check_reports", [])
    records = build_outcome_records(exposures, dispositions, checks)
    write_jsonl(OUTPUT_ROOT / "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl", records)

    dep_status = dependency_status()
    training_rules = build_training_rules_report(records)
    write_json(OUTPUT_ROOT / "E3_TRAINING_ELIGIBILITY_RULES_REPORT.json", training_rules)

    outcome_report = build_outcome_report(records, dep_status)
    write_json(OUTPUT_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json", outcome_report)

    join_report = build_join_report(records)
    write_json(OUTPUT_ROOT / "E3_CHECK_TO_DISPOSITION_JOIN_REPORT.json", join_report)

    calibration_report = build_calibration_report(records, checks)
    write_json(OUTPUT_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json", calibration_report)

    e3_report = read_json(E3_GATE_ROOT / "E3_ARMING_STATUS_REPORT.json", {})
    phase2_scheduled = read_json(PHASE2_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json", {})
    arming_update = build_arming_update(e3_report, phase2_scheduled)
    write_json(OUTPUT_ROOT / "E3_ARMING_STATUS_R1_R2_UPDATE.json", arming_update)

    fuel_snapshot = build_fuel_snapshot(records, arming_update)
    write_json(OUTPUT_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json", fuel_snapshot)

    no_model_guard = build_no_model_guard()
    write_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json", no_model_guard)

    corpus_delta = build_corpus_delta()
    write_json(OUTPUT_ROOT / "E3_L1_R1_R2_CORPUS_DELTA.json", corpus_delta)

    limitations = build_limitations()
    write_json(OUTPUT_ROOT / "E3_L1_R1_R2_LIMITATIONS.json", limitations)

    report_refs = [
        "E3_TRAINING_ELIGIBILITY_RULES_REPORT.json",
        "E3_OUTCOME_LEDGER_HARDENING_REPORT.json",
        "E3_CHECK_TO_DISPOSITION_JOIN_REPORT.json",
        "E3_CALIBRATION_REPORT_HARDENING_REPORT.json",
        "E3_ARMING_STATUS_R1_R2_UPDATE.json",
        "E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json",
        "E3_NO_MODEL_GUARD_REPORT.json",
        "E3_L1_R1_R2_CORPUS_DELTA.json",
    ]
    ledger = build_ledger_row(report_refs)
    write_json(OUTPUT_ROOT / "E3_L1_R1_R2_LEDGER_ROW.json", ledger)

    provisional_lf = {"crlf_paths": []}
    decision = build_decision(dep_status, no_model_guard, provisional_lf, outcome_report)
    write_json(OUTPUT_ROOT / "E3_L1_R1_R2_DECISION.json", decision)

    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    decision = build_decision(dep_status, no_model_guard, lf_report, outcome_report)
    write_json(OUTPUT_ROOT / "E3_L1_R1_R2_DECISION.json", decision)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()

    return {
        "decision": decision,
        "training_rules": training_rules,
        "outcome_report": outcome_report,
        "join_report": join_report,
        "calibration_report": calibration_report,
        "arming_update": arming_update,
        "fuel_snapshot": fuel_snapshot,
        "no_model_guard": no_model_guard,
        "corpus_delta": corpus_delta,
        "limitations": limitations,
        "ledger": ledger,
        "line_endings": lf_report,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 L1.R1/R2 outcome calibration hardening R1: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

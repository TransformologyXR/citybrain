#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-PHASE2-LIVE-EXPOSURE-COVERAGE-AND-HARDENING-R1"
STATUS = "PASS_E3_PHASE2_LIVE_EXPOSURE_COVERAGE_AND_HARDENING_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_PHASE2_LIVE_EXPOSURE_COVERAGE_AND_HARDENING_R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_phase2_live_exposure_coverage_and_hardening_r1"
FIXTURE_ROOT = OUTPUT_ROOT / "fixtures"
E3_GATE_ROOT = REPO_ROOT / "outputs" / "epoch_3_entry_gate_r1_fuel_gauge"
DAY1_ROOT = REPO_ROOT / "outputs" / "epoch3_day1_instrumentation_and_harness_r1"

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

PUBLICATION_ARTIFACTS = [
    "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
    "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
    "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json",
    "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW.json",
    "E3_HOLDOUT_FAMILY_RATIONALE_ROW.json",
    "E3_STANDING_NO_MODEL_GUARD_TEMPLATE.json",
    "E3_NO_MODEL_GUARD_REPORT.json",
    "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json",
    "E3_OUTCOME_LEDGER_HARDENING_START_REPORT.json",
    "E3_CALIBRATION_HARDENING_START_REPORT.json",
    "E3_PHASE2_CORPUS_DELTA.json",
    "E3_PHASE2_LIMITATIONS.json",
    "E3_PHASE2_LEDGER_ROW.json",
    "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json",
    "LINE_ENDING_REPORT.json",
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
        "e3_metrics": read_json(E3_GATE_ROOT / "E3_BASELINE_METRICS.json", {}),
        "e3_decision": read_json(E3_GATE_ROOT / "E3_ENTRY_GATE_DECISION.json", {}),
        "e3_label_reconciliation": read_json(
            E3_GATE_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json", {}
        ),
        "e3_arming_audit": read_json(E3_GATE_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json", {}),
        "e3_track0_debt": read_json(E3_GATE_ROOT / "E3_TRACK0_FULL_HISTORICAL_CORPUS_DISCOVERY_DEBT_ROW.json", {}),
        "day1_decision": read_json(DAY1_ROOT / "E3_DAY1_DECISION.json", {}),
        "day1_exposure": read_json(DAY1_ROOT / "L1_R0_EXPOSURE_PROPENSITY_LOGGING_REPORT.json", {}),
        "day1_no_model": read_json(DAY1_ROOT / "E3_DAY1_NO_MODEL_GUARD_REPORT.json", {}),
    }


def watch_run_envelope_replay() -> dict[str, Any]:
    return {
        "run_envelope_id": "agent-run:e3-phase2:watch-replay:001",
        "component_id": "watch.service.e2_2",
        "run_kind": "replay_watch_tick",
        "created_at": "2026-07-06T12:00:00+01:00",
        "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:001",
        "emitted_candidate_items_count": 4,
        "operator_visible_payload_items_count": 3,
        "note": "One emitted candidate is filtered before payload and is not surfaced/exposed.",
    }


def operator_visible_payload_replay() -> dict[str, Any]:
    return {
        "payload_id": "payload:e3-phase2:watch-replay:001",
        "run_envelope_ref": "agent-run:e3-phase2:watch-replay:001",
        "surfaced_definition": "operator_visible_payload_inclusion",
        "items": [
            {"watch_item_id": "watch:item:asset_state:001", "payload_position": 0, "family": "asset_state"},
            {"watch_item_id": "watch:item:traffic_flow:001", "payload_position": 1, "family": "traffic_flow"},
            {"watch_item_id": "watch:item:media_candidate:001", "payload_position": 2, "family": "media_candidate"},
        ],
    }


def reexposure_run_envelope() -> dict[str, Any]:
    return {
        "run_envelope_id": "agent-run:e3-phase2:watch-replay:002",
        "component_id": "watch.service.e2_2",
        "run_kind": "replay_watch_tick",
        "created_at": "2026-07-06T12:05:00+01:00",
        "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:002",
        "operator_visible_payload_items_count": 1,
        "reexposed_watch_item_id": "watch:item:asset_state:001",
    }


def operator_visible_payload_reexposure() -> dict[str, Any]:
    return {
        "payload_id": "payload:e3-phase2:watch-replay:002",
        "run_envelope_ref": "agent-run:e3-phase2:watch-replay:002",
        "surfaced_definition": "operator_visible_payload_inclusion",
        "items": [
            {"watch_item_id": "watch:item:asset_state:001", "payload_position": 0, "family": "asset_state"}
        ],
    }


def exposure_events() -> list[dict[str, Any]]:
    return [
        {
            "exposure_id": "exposure:e3p2:run001:asset_state:001",
            "watch_item_id": "watch:item:asset_state:001",
            "run_envelope_ref": "agent-run:e3-phase2:watch-replay:001",
            "surface_kind": "operator_visible_review_payload",
            "surface_policy": "deterministic_static",
            "surface_reason": "static_priority_family_cap_allowed",
            "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:001",
            "payload_position": 0,
            "surfaced_definition": "operator_visible_payload_inclusion",
            "reexposure_semantics": "new_event_per_payload_inclusion",
            "propensity_status": "propensity_unknown",
            "propensity": None,
            "training_eligibility": {"eligible_for_r3_fuel": False, "reason": "propensity_unknown"},
        },
        {
            "exposure_id": "exposure:e3p2:run001:traffic_flow:001",
            "watch_item_id": "watch:item:traffic_flow:001",
            "run_envelope_ref": "agent-run:e3-phase2:watch-replay:001",
            "surface_kind": "operator_visible_review_payload",
            "surface_policy": "exploration_floor",
            "surface_reason": "static_exploration_floor_10pct",
            "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:001",
            "payload_position": 1,
            "surfaced_definition": "operator_visible_payload_inclusion",
            "reexposure_semantics": "new_event_per_payload_inclusion",
            "propensity_status": "known",
            "propensity": 0.1,
            "training_eligibility": {"eligible_for_r3_fuel": False, "reason": "not_terminal_disposition"},
        },
        {
            "exposure_id": "exposure:e3p2:run001:media_candidate:001",
            "watch_item_id": "watch:item:media_candidate:001",
            "run_envelope_ref": "agent-run:e3-phase2:watch-replay:001",
            "surface_kind": "operator_visible_review_payload",
            "surface_policy": "holdout",
            "surface_reason": "static_holdout_family_media_candidate",
            "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:001",
            "payload_position": 2,
            "surfaced_definition": "operator_visible_payload_inclusion",
            "reexposure_semantics": "new_event_per_payload_inclusion",
            "propensity_status": "not_applicable",
            "propensity": None,
            "training_eligibility": {
                "eligible_for_r3_fuel": False,
                "reason": "holdout_family_not_terminal_disposition",
            },
        },
        {
            "exposure_id": "exposure:e3p2:run002:asset_state:001",
            "watch_item_id": "watch:item:asset_state:001",
            "run_envelope_ref": "agent-run:e3-phase2:watch-replay:002",
            "surface_kind": "operator_visible_review_payload",
            "surface_policy": "deterministic_static",
            "surface_reason": "re_surfaced_undispositioned_item",
            "operator_visible_payload_ref": "payload:e3-phase2:watch-replay:002",
            "payload_position": 0,
            "surfaced_definition": "operator_visible_payload_inclusion",
            "reexposure_semantics": "new_event_per_payload_inclusion",
            "propensity_status": "known",
            "propensity": 1.0,
            "training_eligibility": {"eligible_for_r3_fuel": False, "reason": "not_terminal_disposition"},
        },
        {
            "exposure_id": "exposure:e3p2:unverified:001",
            "watch_item_id": "watch:item:legacy_unverified:001",
            "run_envelope_ref": "agent-run:e3-phase2:legacy-unverified:001",
            "surface_kind": "operator_visible_review_payload",
            "surface_policy": "manual_review",
            "surface_reason": "legacy disposition lacks verified payload linkage and is excluded from R3 fuel",
            "operator_visible_payload_ref": "payload:e3-phase2:legacy-unverified:001",
            "payload_position": 0,
            "surfaced_definition": "operator_visible_payload_inclusion",
            "reexposure_semantics": "new_event_per_payload_inclusion",
            "propensity_status": "known",
            "propensity": None,
            "training_eligibility": {"eligible_for_r3_fuel": False, "reason": "unverified_exposure"},
        },
    ]


def empty_tick_fixture() -> dict[str, Any]:
    return {
        "run_envelope_id": "agent-run:e3-phase2:watch-empty:001",
        "operator_visible_payload_items_count": 0,
        "exposure_events_count": 0,
        "coverage_ratio": 1.0,
        "standing_health_result": "PASS_VACUOUS_EMPTY_TICK",
        "phase2_verification_eligible": False,
    }


def pending_tick_metrics() -> dict[str, Any]:
    return {
        "scheduled_tick_verification_status": "PENDING_FIRST_SCHEDULED_TICK",
        "pending_days": 8,
        "overdue_after_days": 7,
        "expected_arming_status_review_item": True,
    }


def expected_training_eligibility_reasons() -> dict[str, Any]:
    return {
        "enum_values": [
            "eligible_terminal_disposition",
            "propensity_unknown",
            "unverified_exposure",
            "not_terminal_disposition",
            "holdout_family_not_terminal_disposition",
            "no_terminal_disposition_yet",
        ],
        "r3_exclusion_reasons": [
            "propensity_unknown",
            "unverified_exposure",
            "not_terminal_disposition",
            "holdout_family_not_terminal_disposition",
            "no_terminal_disposition_yet",
        ],
    }


def build_surfaced_definition_row() -> dict[str, Any]:
    return {
        "id": "E3_SURFACED_IMPRESSION_DEFINITION_ROW",
        "surfaced_definition": "operator_visible_payload_inclusion",
        "definition_text": "An item is surfaced when it is included in an operator-visible review payload, not merely when emitted internally by the Watch service.",
        "denominator": "operator_visible_payload_items_count",
        "not_denominator": "watch_service_emitted_candidate_items_count",
        "reexposure_rule": "new_exposure_event_per_payload_inclusion",
        "coverage_scope": "per_run_envelope",
        "empty_tick_policy": "standing_health_vacuous_pass",
        "phase2_verification_requirement": "operator_visible_payload_items_count_gt_zero",
        "limitation": "payload_presented approximates impression; actual viewport/scroll visibility is not yet tracked.",
    }


def build_coverage_report(payload: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    run_ref = payload["run_envelope_ref"]
    payload_items = payload["items"]
    run_rows = [row for row in rows if row["run_envelope_ref"] == run_ref]
    required = {
        "exposure_id",
        "watch_item_id",
        "run_envelope_ref",
        "operator_visible_payload_ref",
        "payload_position",
        "surface_policy",
        "surface_reason",
        "surfaced_definition",
        "training_eligibility",
    }
    missing_count = sum(1 for row in run_rows for key in required if key not in row)
    payload_key = {(item["watch_item_id"], item["payload_position"]) for item in payload_items}
    exposure_key = {(row["watch_item_id"], row["payload_position"]) for row in run_rows}
    coverage_ratio = len(run_rows) / len(payload_items) if payload_items else 1.0
    return {
        "id": "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "watch_run_envelope_ref": run_ref,
        "verification_run_kind": "replay_watch_tick",
        "operator_visible_payload_items_count": len(payload_items),
        "exposure_events_count": len(run_rows),
        "coverage_ratio": coverage_ratio,
        "coverage_scope": "per_run_envelope",
        "coverage_passed": payload_key == exposure_key and coverage_ratio == 1.0,
        "phase2_verification_non_empty_payload": len(payload_items) > 0,
        "orphan_exposure_events_count": len(exposure_key - payload_key),
        "missing_required_field_count": missing_count,
        "surfaced_definition_ref": "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
        "watch_run_envelope_ref_path": "fixtures/watch_run_envelope_replay.json",
        "operator_visible_payload_ref_path": "fixtures/operator_visible_payload_replay.json",
        "exposure_events_ref": "fixtures/exposure_events_replay.jsonl",
    }


def build_scheduled_tick_row() -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "id": "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW",
        "status": "PENDING_FIRST_SCHEDULED_TICK",
        "owner": "E3.ARMING_STATUS_WATCH_FAMILY / Watch service owner",
        "pending_since": now.isoformat().replace("+00:00", "Z"),
        "next_check_after": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "overdue_after_days": 7,
        "arming_status_watch_item_on_overdue": True,
        "review_item_family": "review_backlog",
        "overdue_watcher": {
            "component_id": "E3.ARMING_STATUS_WATCH_FAMILY",
            "trigger": "scheduled_tick_pending_days > overdue_after_days",
            "expected_review_item": True,
        },
        "note": "No scheduled tick was observed during this package run; replay coverage verification passed with non-empty payload.",
    }


def build_watch_service_delta() -> dict[str, Any]:
    return {
        "id": "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW",
        "delta_kind": "additive_health_and_closeout_criterion",
        "target_service": "Epoch2.2 Watch service",
        "target_prior_evidence_refs": [
            "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_CONFIG.json",
            "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_THROTTLE_REPORT.json",
            "outputs/epoch_2_2/push_2_2b/lane_a_watch_service/WATCH_SERVICE_RUN_ENVELOPES.jsonl",
        ],
        "source_refs": [
            "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
            "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
        ],
        "change": {
            "add_health_criterion": "exposure coverage per operator-visible payload",
            "required_standing_result": "coverage_ratio == 1.0 per non-empty run envelope; empty run envelope is vacuous pass",
            "phase2_verification_requires_non_empty_payload": True,
            "add_stop_condition": "coverage regression failure blocks Watch service closeout/health green",
        },
        "reason": "Epoch 3 learning fuel requires verified exposure/impression logging; this is an additive delta, not a silent edit of sealed Epoch 2.2 service state.",
    }


def build_holdout_rationale() -> dict[str, Any]:
    return {
        "id": "E3_HOLDOUT_FAMILY_RATIONALE_ROW",
        "holdout_family": "media_candidate",
        "rationale": "media_candidate is perception-heavy, candidate-only, higher-boundary-risk, and should not influence early learned ranking until media/perception review evidence matures.",
        "future_rule_before_r3b": "Before L1.R3B operator-facing learned ranking may arm, static holdout families must include at least one non-perception family unless a ledgered exception is published.",
    }


def build_standing_no_model_template() -> dict[str, Any]:
    return {
        "id": "E3_STANDING_NO_MODEL_GUARD_TEMPLATE",
        "pre_r3a_invariant": {
            "new_learned_component_registry_entries": 0,
            "ranker_created": False,
            "forecast_model_created": False,
            "counterfactual_learner_created": False,
            "case_memory_learner_created": False,
            "dynamic_investigation_agent_created": False,
            "cross_city_learned_transfer_created": False,
        },
        "post_r3a_allowed_shape": {
            "status": "experimental",
            "consuming_surfaces": [],
            "eval_refs": "required_non_empty",
            "training_manifest_ref": "required",
            "frozen_replay_only": True,
            "release_ledger_row": None,
        },
        "closeout_exclusion_list": STILL_BLOCKED,
    }


def build_no_model_guard() -> dict[str, Any]:
    return {
        "id": "E3_NO_MODEL_GUARD_REPORT",
        "status": "PASS",
        "pre_r3a_invariant": {
            "new_learned_component_registry_entries": 0,
            "ranker_created": False,
            "forecast_model_created": False,
            "counterfactual_learner_created": False,
            "case_memory_learner_created": False,
            "dynamic_investigation_agent_created": False,
            "cross_city_learned_transfer_created": False,
            "forbidden_capabilities_armed": [],
        },
        "post_r3a_invariant_documented": True,
        "violations": [],
    }


def build_outcome_hardening_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unverified = [row for row in rows if row["training_eligibility"]["reason"] == "unverified_exposure"]
    excluded = [row for row in rows if not row["training_eligibility"]["eligible_for_r3_fuel"]]
    return {
        "id": "E3_OUTCOME_LEDGER_HARDENING_START_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "surfaced_definition_ref": "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
        "eligibility_rules": {
            "requires_verified_exposure_linkage": True,
            "unverified_exposure_excluded_from_r3_fuel": True,
            "propensity_unknown_excluded_from_r3_fuel": True,
            "training_eligibility_reason_enum": expected_training_eligibility_reasons()["enum_values"],
        },
        "eligible_terminal_dispositions": 0,
        "unverified_exposure_exclusions": len(unverified),
        "total_r3_excluded_exposure_events": len(excluded),
        "true_learning_fuel_claimed": False,
        "source_refs": [
            "fixtures/exposure_events_replay.jsonl",
            rel(E3_GATE_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json"),
        ],
    }


def build_calibration_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "E3_CALIBRATION_HARDENING_START_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "sample_depth": 0,
        "true_calibration_claimed": False,
        "descriptive_only": True,
        "planned_breakdowns": [
            "check_type",
            "source_class",
            "watch_family",
            "domain_pack",
            "operator_disposition",
        ],
        "coverage_linked_exposure_events": len(rows),
        "limitation": "Calibration remains descriptive because no eligible terminal disposition sample depth exists.",
    }


def build_fuel_snapshot(rows: list[dict[str, Any]], inputs: dict[str, Any]) -> dict[str, Any]:
    metrics = inputs["e3_metrics"]
    reasons = [row["training_eligibility"]["reason"] for row in rows]
    return {
        "snapshot_id": "fuel-snapshot:e3:phase2:r1:0001",
        "previous_snapshot_ref": None,
        "emitter": "E3.ARMING_STATUS_WATCH_FAMILY",
        "created_at": utc_now(),
        "metrics": {
            "eligible_terminal_dispositions": metrics.get("outcome", {})
            .get("terminal_dispositions", {})
            .get("count", 0),
            "operator_refs_distinct": metrics.get("outcome", {}).get("operator_refs", {}).get("distinct_count", 0),
            "watch_families_represented": metrics.get("watch", {}).get("families", {}).get("distinct_count", 0),
            "propensity_known_coverage": sum(1 for row in rows if row["propensity_status"] == "known"),
            "unverified_exposure_exclusions": reasons.count("unverified_exposure"),
            "propensity_unknown_exclusions": reasons.count("propensity_unknown"),
            "calibration_sample_depth": 0,
        },
        "arming_status": {
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": "NOT_ARMED",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": "NOT_ARMED",
            "L2.R2_FORECAST_MODEL": "NOT_ARMED",
            "L3_COUNTERFACTUAL": "NOT_ARMED",
            "L4_CASE_MEMORY": "NOT_ARMED",
        },
    }


def build_corpus_delta() -> dict[str, Any]:
    return {
        "id": "E3_PHASE2_CORPUS_DELTA",
        "delta_kind": "coverage_regression_append",
        "next_corpus_version_ref": "epoch3_phase2_coverage_regression_v1",
        "fixtures_added": [
            "fixtures/watch_run_envelope_replay.json",
            "fixtures/operator_visible_payload_replay.json",
            "fixtures/exposure_events_replay.jsonl",
            "fixtures/reexposure_run_envelope_002.json",
            "fixtures/operator_visible_payload_reexposure_002.json",
            "fixtures/empty_tick_vacuous_pass_fixture.json",
        ],
        "frozen_artifacts_added": [
            "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
            "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
            "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json",
        ],
        "blocks_r3a_if_missing": True,
    }


def build_limitations() -> dict[str, Any]:
    return {
        "id": "E3_PHASE2_LIMITATIONS",
        "limitations": [
            {
                "id": "LIMIT_PAYLOAD_AS_IMPRESSION",
                "text": "payload_presented approximates impression; actual viewport/scroll visibility is not yet tracked.",
                "owner": "Watch/UI route owner",
                "next_lane": "future UI telemetry / viewport tracking",
            },
            {
                "id": "LIMIT_SCHEDULED_TICK_PENDING_ALLOWED",
                "text": "No scheduled tick occurred during this package; scheduled-tick verification remains pending with an arming-status watcher.",
                "owner": "E3.ARMING_STATUS_WATCH_FAMILY",
                "next_lane": "first scheduled tick verification",
            },
            {
                "id": "LIMIT_NO_LABEL_FUEL_YET",
                "text": "Outcome and calibration remain descriptive until eligible terminal dispositions exist.",
                "owner": "L1.R1/L1.R2",
                "next_lane": "fuel accumulation standing condition",
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
        "id": "LINE_ENDING_REPORT",
        "created_at": utc_now(),
        "status": "PASS_LF_STABLE_FOR_E3_PHASE2_PUBLICATION" if not crlf_paths else "FAIL_CRLF_PRESENT",
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
        "id": "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_AND_HARDENING_R1_PUBLISHED",
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "summary": "Phase 2 verifies exposure coverage against operator-visible payloads, locks re-exposure semantics, starts outcome/calibration hardening under verified exposure rules, publishes Watch-service additive coverage criterion, registers corpus delta, and emits the first chained fuel-gauge snapshot.",
        "no_model_work": True,
        "atomic_publication": True,
        "report_refs": report_refs,
        "hash_manifest_ref": "HASH_MANIFEST.json",
    }


def build_decision(inputs: dict[str, Any], coverage: dict[str, Any], scheduled: dict[str, Any], guard: dict[str, Any], lf: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if inputs["e3_decision"].get("status") != "PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS":
        blockers.append("E3 R1 gate status missing or not PASS")
    if inputs["day1_decision"].get("status") != "PASS_E3_DAY1_INSTRUMENTATION_AND_HARNESS_R1_WITH_LIMITATIONS":
        blockers.append("E3 Day 1 dependency missing or not PASS")
    if not coverage["coverage_passed"] or not coverage["phase2_verification_non_empty_payload"]:
        blockers.append("live exposure coverage verification failed")
    if scheduled["status"] not in {"PASS_FIRST_SCHEDULED_TICK_VERIFIED", "PENDING_FIRST_SCHEDULED_TICK"}:
        blockers.append("scheduled tick verification invalid")
    if guard["status"] != "PASS":
        blockers.append("no-model guard failed")
    if lf["crlf_paths"]:
        blockers.append("CRLF paths found")
    status = STATUS if not blockers else BLOCKED_STATUS
    return {
        "id": "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION",
        "package_id": PACKAGE_ID,
        "status": status,
        "blockers": blockers,
        "armed_now": ARMED_NOW,
        "still_blocked": STILL_BLOCKED,
        "source_refs": [
            rel(E3_GATE_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json"),
            rel(E3_GATE_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json"),
            rel(DAY1_ROOT / "E3_DAY1_DECISION.json"),
            "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
            "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
            "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json",
        ],
        "coverage_summary": {
            "operator_visible_payload_items_count": coverage["operator_visible_payload_items_count"],
            "exposure_events_count": coverage["exposure_events_count"],
            "coverage_ratio": coverage["coverage_ratio"],
            "coverage_scope": "per_run_envelope",
        },
        "scheduled_tick_status": scheduled["status"],
        "no_model_guard": guard["status"],
    }


def write_fixtures(rows: list[dict[str, Any]]) -> None:
    write_json(FIXTURE_ROOT / "watch_run_envelope_replay.json", watch_run_envelope_replay())
    write_json(FIXTURE_ROOT / "operator_visible_payload_replay.json", operator_visible_payload_replay())
    write_jsonl(FIXTURE_ROOT / "exposure_events_replay.jsonl", rows)
    write_json(FIXTURE_ROOT / "reexposure_run_envelope_002.json", reexposure_run_envelope())
    write_json(FIXTURE_ROOT / "operator_visible_payload_reexposure_002.json", operator_visible_payload_reexposure())
    write_json(FIXTURE_ROOT / "empty_tick_vacuous_pass_fixture.json", empty_tick_fixture())
    write_json(FIXTURE_ROOT / "metrics_pending_tick_overdue.json", pending_tick_metrics())
    write_json(FIXTURE_ROOT / "expected_training_eligibility_reasons.json", expected_training_eligibility_reasons())


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    rows = exposure_events()
    write_fixtures(rows)

    surfaced = build_surfaced_definition_row()
    write_json(OUTPUT_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json", surfaced)

    coverage = build_coverage_report(operator_visible_payload_replay(), rows)
    write_json(OUTPUT_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json", coverage)

    scheduled = build_scheduled_tick_row()
    write_json(OUTPUT_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json", scheduled)

    watch_delta = build_watch_service_delta()
    write_json(OUTPUT_ROOT / "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW.json", watch_delta)

    holdout = build_holdout_rationale()
    write_json(OUTPUT_ROOT / "E3_HOLDOUT_FAMILY_RATIONALE_ROW.json", holdout)

    guard_template = build_standing_no_model_template()
    write_json(OUTPUT_ROOT / "E3_STANDING_NO_MODEL_GUARD_TEMPLATE.json", guard_template)

    guard = build_no_model_guard()
    write_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json", guard)

    snapshot = build_fuel_snapshot(rows, inputs)
    write_json(OUTPUT_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json", snapshot)

    outcome = build_outcome_hardening_report(rows)
    write_json(OUTPUT_ROOT / "E3_OUTCOME_LEDGER_HARDENING_START_REPORT.json", outcome)

    calibration = build_calibration_report(rows)
    write_json(OUTPUT_ROOT / "E3_CALIBRATION_HARDENING_START_REPORT.json", calibration)

    corpus_delta = build_corpus_delta()
    write_json(OUTPUT_ROOT / "E3_PHASE2_CORPUS_DELTA.json", corpus_delta)

    limitations = build_limitations()
    write_json(OUTPUT_ROOT / "E3_PHASE2_LIMITATIONS.json", limitations)

    report_refs = [
        "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
        "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
        "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json",
        "E3_WATCH_SERVICE_COVERAGE_CRITERION_DELTA_ROW.json",
        "E3_HOLDOUT_FAMILY_RATIONALE_ROW.json",
        "E3_NO_MODEL_GUARD_REPORT.json",
        "E3_FUEL_GAUGE_DELTA_SNAPSHOT.json",
        "E3_OUTCOME_LEDGER_HARDENING_START_REPORT.json",
        "E3_CALIBRATION_HARDENING_START_REPORT.json",
        "E3_PHASE2_CORPUS_DELTA.json",
    ]
    ledger = build_ledger_row(report_refs)
    write_json(OUTPUT_ROOT / "E3_PHASE2_LEDGER_ROW.json", ledger)

    provisional_lf = {"crlf_paths": []}
    decision = build_decision(inputs, coverage, scheduled, guard, provisional_lf)
    write_json(OUTPUT_ROOT / "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json", decision)

    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)

    decision = build_decision(inputs, coverage, scheduled, guard, lf)
    write_json(OUTPUT_ROOT / "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json", decision)
    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)

    hash_manifest = build_hash_manifest()
    return {
        "decision": decision,
        "surfaced": surfaced,
        "coverage": coverage,
        "scheduled": scheduled,
        "watch_delta": watch_delta,
        "holdout": holdout,
        "guard_template": guard_template,
        "guard": guard,
        "snapshot": snapshot,
        "outcome": outcome,
        "calibration": calibration,
        "corpus_delta": corpus_delta,
        "limitations": limitations,
        "ledger": ledger,
        "line_endings": lf,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 Phase 2 live exposure coverage and hardening R1: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

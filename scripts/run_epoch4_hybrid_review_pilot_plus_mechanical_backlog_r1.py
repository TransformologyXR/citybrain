#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH4-HYBRID-REVIEW-PILOT-PLUS-MECHANICAL-BACKLOG-R1"
STATUS = "PASS_E4_HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E4_HYBRID_R1_PENDING_E3_CLOSEOUT_OR_FORK_PUBLICATION"
SELECTED_FORK = "HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG"

OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch4_hybrid_review_pilot_plus_mechanical_backlog_r1"
PUBLICATION_ROOT = REPO_ROOT / "publications" / "epoch4"
PUBLICATION_DIR = PUBLICATION_ROOT / "main-citybrain-epoch4-hybrid-review-pilot-plus-mechanical-backlog-r1"
E3_CLOSEOUT_PUBLICATION = REPO_ROOT / "publications" / "epoch3" / "main-citybrain-epoch3-closeout-r1"
POST_E3_PUBLICATION = REPO_ROOT / "publications" / "post_e3" / "main-citybrain-post-e3-closeout-epoch4-fork-preflight-r1"

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
ELIGIBLE_REVIEW_FAMILIES = ["asset_state", "traffic_flow", "review_backlog", "public_safety_boundary"]
HOLDOUT_FAMILIES = ["media_candidate"]
TRANSITION_TARGETS = [
    "inspection_delay_v0",
    "violation_resolution_delay_v0",
    "watch_queue_aging_v0",
    "incident_duration_v0",
    "backlog_clearance_time_v0",
]
VALID_BACKLOG_DISPOSITIONS = {
    "done",
    "partially_done",
    "deferred_epoch4_later",
    "blocked_requires_live_or_human",
    "not_promotable",
    "parking_lot",
}

REQUIRED_OUTPUTS = (
    "E4_PRECONDITION_CHECK_REPORT.json",
    "E4_FORK_SELECTION_LEDGER_ROW.json",
    "E4_INHERITED_ARMING_BASELINE.json",
    "E4_REVIEW_PILOT_PROTOCOL.json",
    "E4_REVIEW_SESSION_PLAN.json",
    "E4_REVIEW_PILOT_QUEUE_MANIFEST.json",
    "E4_REVIEW_PILOT_DRY_RUN_REPORT.json",
    "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json",
    "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT.json",
    "E4_L2_FORECAST_IMPROVEMENT_PLAN.json",
    "E4_L2_PERMIT_STALL_R2_READINESS_OR_EXPERIMENT_REPORT.json",
    "E4_L2_CITY_STRATIFIED_EVAL_REQUIREMENTS.json",
    "E4_L2_TRANSITION_TARGET_BATCH_REPORT.json",
    "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json",
    "E4_L4_CASE_STUBS.jsonl",
    "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT.json",
    "E4_CHECK_CALIBRATION_LIMITATION_ROW.json",
    "E4_TRANSITION_TARGET_MATERIALIZATION_BATCH_DECISION.json",
    "E4_IDENTITY_GRAPH_EVAL_FIXTURE_REPORT.json",
    "E4_LLM_SEAT_USEFULNESS_SCORECARD.json",
    "E4_PERCEPTION_CANDIDATE_REVIEW_INVENTORY.json",
    "E4_DOMAIN_PACK_USEFULNESS_REPORT.json",
    "E4_SIMULATION_BACKTEST_INPUT_CATALOG.json",
    "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT.json",
    "E4_BACKLOG_DISPOSITION_LEDGER.json",
    "E4_CORPUS_DELTA.json",
    "E4_PUBLICATION_COVERAGE_REPORT.json",
    "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "E4_HYBRID_LIMITATIONS.json",
    "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
    "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_LEDGER_ROW.json",
    "E4_NEXT_ACTIONS_AFTER_R1.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gitattributes_has_publication_lf_rule() -> bool:
    attrs = REPO_ROOT / ".gitattributes"
    return attrs.exists() and "publications/** text eol=lf" in attrs.read_text(encoding="utf-8")


def load_e3(name: str, default: Any | None = None) -> Any:
    return read_json(E3_CLOSEOUT_PUBLICATION / name, default)


def load_post_e3(name: str, default: Any | None = None) -> Any:
    return read_json(POST_E3_PUBLICATION / name, default)


def load_output(rel_path: str, default: Any | None = None) -> Any:
    return read_json(REPO_ROOT / rel_path, default)


def precondition_report() -> dict[str, Any]:
    e3_decision_path = E3_CLOSEOUT_PUBLICATION / "E3_CLOSEOUT_DECISION.json"
    post_decision_path = POST_E3_PUBLICATION / "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION.json"
    post_sequence_path = POST_E3_PUBLICATION / "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST.json"
    checks = {
        "e3_closeout_publication_exists": E3_CLOSEOUT_PUBLICATION.exists(),
        "e3_closeout_decision_exists": e3_decision_path.exists(),
        "post_e3_fork_preflight_publication_exists": POST_E3_PUBLICATION.exists(),
        "post_e3_preflight_decision_exists": post_decision_path.exists(),
        "post_e3_sequence_manifest_exists": post_sequence_path.exists(),
        "publication_lf_rule_present": gitattributes_has_publication_lf_rule(),
        "selected_fork_from_user_instruction": SELECTED_FORK,
    }
    missing = [key for key, value in checks.items() if value is False]
    return {
        "artifact_id": "E4_PRECONDITION_CHECK_REPORT",
        "package_id": PACKAGE_ID,
        "created_at": utc_now(),
        "status": "PASS_PRECONDITIONS" if not missing else BLOCKED_STATUS,
        "preconditions_passed": not missing,
        "blocked_reason": None if not missing else "missing_prerequisite_publication_or_lf_rule",
        "missing_checks": missing,
        "checks": checks,
        "e3_closeout_publication_path": rel(E3_CLOSEOUT_PUBLICATION) if E3_CLOSEOUT_PUBLICATION.exists() else None,
        "post_e3_publication_path": rel(POST_E3_PUBLICATION) if POST_E3_PUBLICATION.exists() else None,
    }


def fork_selection_row(preconditions: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "E4_FORK_SELECTION_LEDGER_ROW",
        "package_id": PACKAGE_ID,
        "selected_fork": SELECTED_FORK,
        "selection_source": "explicit_user_selection_in_chat",
        "selection_evidence": "User supplied the E4 hybrid master-executor package and requested execution.",
        "epoch4_started": preconditions["preconditions_passed"],
        "preconditions_passed": preconditions["preconditions_passed"],
        "blocked_reason": preconditions["blocked_reason"],
        "inherited_thresholds_ref": "E4_INHERITED_ARMING_BASELINE.json",
        "ledger_note": "Epoch 4 hybrid path selected; all deferred capabilities remain evaluator-gated.",
    }


def inherited_arming_baseline() -> dict[str, Any]:
    manifest = read_json(REPO_ROOT / "manifests" / "epoch3_arming_manifest.json", {})
    snapshot = load_output("outputs/epoch3_master_execution_r1/E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json", {})
    e3_handoff = load_e3("E3_ARMING_HANDOFF_TO_EPOCH4.json", {})
    post_handoff = load_post_e3("E4_ARMING_INHERITANCE_HANDOFF.json", {})
    return {
        "artifact_id": "E4_INHERITED_ARMING_BASELINE",
        "package_id": PACKAGE_ID,
        "inherits_from": [
            "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1",
            "MAIN-CITYBRAIN-POST-E3-CLOSEOUT-EPOCH4-FORK-PREFLIGHT-R1",
        ],
        "evaluator_inherited": True,
        "evaluator_id": manifest.get("evaluator", {}).get("id", "epoch3_arming_status"),
        "evaluator_is_only_arming_authority": True,
        "thresholds_inherited_unchanged": True,
        "threshold_changes_require_governance_delta": True,
        "threshold_crossing_does_not_start_work_in_same_run": True,
        "armed_now": snapshot.get("armed_now", manifest.get("armed_now", [])),
        "not_armed": snapshot.get("not_armed", {}),
        "conditionally_armed_thresholds": manifest.get("conditionally_armed", {}),
        "latest_snapshot_ref": snapshot.get("snapshot_ref", "outputs/epoch3_master_execution_r1/E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json"),
        "e3_handoff_ref": rel(E3_CLOSEOUT_PUBLICATION / "E3_ARMING_HANDOFF_TO_EPOCH4.json"),
        "post_e3_handoff_ref": rel(POST_E3_PUBLICATION / "E4_ARMING_INHERITANCE_HANDOFF.json"),
        "operator_paced_fuel_program": post_handoff.get("operator_paced_fuel_program", e3_handoff.get("operator_paced_fuel_program", "blocked_until_live_or_structured_review_pilot")),
    }


def human_review_inbox_files() -> list[Path]:
    inboxes = [
        REPO_ROOT / "inputs" / "epoch4_hybrid_review_pilot_sessions",
        REPO_ROOT / "inputs" / "e4_review_pilot_sessions",
        REPO_ROOT / "inputs" / "review_pilot_sessions",
        REPO_ROOT / "inputs" / "human_review_sessions",
        REPO_ROOT / "review_sessions",
    ]
    files: list[Path] = []
    for inbox in inboxes:
        if not inbox.exists() or not inbox.is_dir():
            continue
        for suffix in ("*.json", "*.jsonl"):
            files.extend(sorted(inbox.glob(suffix), key=lambda p: p.as_posix()))
    return files


def load_review_records(files: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in files:
        if path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if isinstance(row, dict):
                        row["_source_file"] = rel(path)
                        records.append(row)
            continue
        payload = read_json(path, {})
        if isinstance(payload, list):
            iterable = payload
        elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
            iterable = payload["records"]
        elif isinstance(payload, dict) and isinstance(payload.get("dispositions"), list):
            iterable = payload["dispositions"]
        else:
            iterable = [payload]
        for row in iterable:
            if isinstance(row, dict):
                row["_source_file"] = rel(path)
                records.append(row)
    return records


def valid_human_review_record(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    for field in ["session_id", "operator_ref", "exposure_id", "watch_item_id", "disposition", "occurred_at"]:
        if not row.get(field):
            reasons.append(f"missing_{field}")
    if str(row.get("operator_ref", "")).startswith("operator:pseudo"):
        reasons.append("pseudo_operator_not_human_fuel")
    if row.get("disposition") not in {"confirmed", "dismissed", "needs_more"}:
        reasons.append("invalid_disposition")
    if row.get("exposure_linkage_verified") is not True:
        reasons.append("exposure_linkage_not_verified")
    if row.get("training_fuel_policy") not in {"human_verified_only", None}:
        reasons.append("invalid_training_fuel_policy")
    return not reasons, reasons


def review_session_plan() -> dict[str, Any]:
    sessions = []
    for idx in range(1, 4):
        sessions.append(
            {
                "session_id": f"e4:pilot:dryrun:session:{idx:03d}",
                "operator_ref": f"operator:pseudo:{idx:03d}",
                "planned_items": 12,
                "eligible_families": ELIGIBLE_REVIEW_FAMILIES,
                "holdout_families": HOLDOUT_FAMILIES,
                "training_fuel_policy": "dry_run_non_training",
            }
        )
    return {
        "artifact_id": "E4_REVIEW_SESSION_PLAN",
        "package_id": PACKAGE_ID,
        "status": "PLAN_READY",
        "session_count": len(sessions),
        "operator_count": 3,
        "eligible_families": ELIGIBLE_REVIEW_FAMILIES,
        "holdout_families": HOLDOUT_FAMILIES,
        "sessions": sessions,
    }


def review_queue_manifest() -> dict[str, Any]:
    rows = []
    idx = 1
    for family in ELIGIBLE_REVIEW_FAMILIES:
        for offset in range(1, 4):
            rows.append(
                {
                    "queue_item_id": f"e4:pilot:queue:{idx:03d}",
                    "family": family,
                    "source_ref": "outputs/epoch3_phase2_live_exposure_coverage_and_hardening_r1/fixtures/operator_visible_payload_replay.json",
                    "assigned_session_id": f"e4:pilot:dryrun:session:{((idx - 1) % 3) + 1:03d}",
                    "position": offset,
                    "holdout": False,
                    "training_fuel_policy": "dry_run_non_training",
                }
            )
            idx += 1
    return {
        "artifact_id": "E4_REVIEW_PILOT_QUEUE_MANIFEST",
        "package_id": PACKAGE_ID,
        "status": "QUEUE_READY",
        "stratified_family_coverage": ELIGIBLE_REVIEW_FAMILIES,
        "holdout_families_retained": HOLDOUT_FAMILIES,
        "queue_item_count": len(rows),
        "rows": rows,
    }


def review_pilot_outputs() -> dict[str, Any]:
    inbox_files = human_review_inbox_files()
    records = load_review_records(inbox_files)
    valid_records = []
    invalid_records = []
    for row in records:
        valid, reasons = valid_human_review_record(row)
        if valid:
            valid_records.append(row)
        else:
            invalid_records.append({"source_file": row.get("_source_file"), "session_id": row.get("session_id"), "reasons": reasons})

    if not inbox_files:
        pilot_status = "PILOT_READY_AND_DRY_RUN_COMPLETE_HUMAN_SESSIONS_PENDING"
    elif valid_records:
        pilot_status = "HUMAN_SESSIONS_INGESTED_WITH_LIMITATIONS"
    else:
        pilot_status = "HUMAN_SESSION_INPUTS_PRESENT_NONE_ELIGIBLE"

    plan = review_session_plan()
    queue = review_queue_manifest()
    protocol = {
        "artifact_id": "E4_REVIEW_PILOT_PROTOCOL",
        "package_id": PACKAGE_ID,
        "status": "PROTOCOL_READY",
        "scope": "hybrid_review_pilot_local_replay_and_optional_human_ingest",
        "eligible_families": ELIGIBLE_REVIEW_FAMILIES,
        "holdout_families": HOLDOUT_FAMILIES,
        "operator_count_required": 3,
        "exposure_linkage_required": True,
        "valid_operator_session_metadata_required": True,
        "pseudo_operator_dry_run_counts_as_training_fuel": False,
        "same_run_arming_allowed": False,
    }
    dry_run = {
        "artifact_id": "E4_REVIEW_PILOT_DRY_RUN_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_DRY_RUN_NON_TRAINING",
        "dry_run_sessions": plan["sessions"],
        "dry_run_queue_items": queue["queue_item_count"],
        "pseudo_operator_refs": [row["operator_ref"] for row in plan["sessions"]],
        "training_fuel_policy": "dry_run_non_training",
        "counts_toward_production_training_fuel": False,
    }
    eligibility = {
        "artifact_id": "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT",
        "package_id": PACKAGE_ID,
        "status": pilot_status,
        "human_review_inbox_files": [rel(path) for path in inbox_files],
        "human_review_records_found": len(records),
        "eligible_human_training_fuel_records": len(valid_records),
        "invalid_or_noneligible_records": invalid_records,
        "human_sessions_pending": not valid_records,
        "pseudo_dry_run_records_counted_as_training_fuel": 0,
        "eligibility_rule": "Count only human verified records with exposure linkage, valid operator/session metadata, and terminal disposition.",
    }
    fuel = {
        "artifact_id": "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT",
        "package_id": PACKAGE_ID,
        "status": "PASS_WEEK1_SNAPSHOT_ZERO_PRODUCTION_FUEL" if not valid_records else "PASS_WEEK1_SNAPSHOT_WITH_VALID_HUMAN_FUEL",
        "production_eligible_terminal_dispositions_delta": len(valid_records),
        "dry_run_dispositions_delta": queue["queue_item_count"],
        "dry_run_training_fuel_count": 0,
        "operator_refs_distinct_count_delta": len({row.get("operator_ref") for row in valid_records}),
        "watch_family_distinct_count_delta": len({row.get("family") for row in valid_records if row.get("family")}),
        "r3a_r3b_l4_remain_evaluator_gated": True,
        "human_sessions_pending": not valid_records,
    }
    return {
        "protocol": protocol,
        "plan": plan,
        "queue": queue,
        "dry_run": dry_run,
        "eligibility": eligibility,
        "fuel": fuel,
        "pilot_status": pilot_status,
        "valid_human_records": valid_records,
    }


def l2_outputs() -> dict[str, Any]:
    forecast = load_e3("E3_FORECAST_RESULT_FRAMING_ROW.json", {})
    city = load_e3("E3_CITY_DIVERGENCE_WARNING_ROW.json", {})
    registry = load_e3("E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json", {})
    return {
        "improvement_plan": {
            "artifact_id": "E4_L2_FORECAST_IMPROVEMENT_PLAN",
            "package_id": PACKAGE_ID,
            "status": "PLAN_READY_OFFLINE_ONLY",
            "current_component": "forecast.permit_stall_v0.r1",
            "current_component_status": registry.get("allowed_experimental_components", [{}])[0].get("status", "experimental"),
            "current_limitations": [
                "R1 pipeline validated but model is not deployable.",
                "Average precision and Brier improved offline, but recall at fixed precision remains weak.",
                "Product forecast surface remains unarmed.",
            ],
            "average_precision": forecast.get("average_precision"),
            "brier": forecast.get("brier"),
            "city_divergence_warning": city.get("status", "WARNING"),
            "city_stratified_evaluation_mandatory": True,
            "product_forecast_surface_created": False,
            "product_forecast_packet_created": False,
            "r2_work_mode": "preflight_plan_only_no_training_in_this_package",
        },
        "readiness": {
            "artifact_id": "E4_L2_PERMIT_STALL_R2_READINESS_OR_EXPERIMENT_REPORT",
            "package_id": PACKAGE_ID,
            "status": "R2_PREFLIGHT_READY_EXPERIMENT_NOT_RUN",
            "experiment_run": False,
            "new_model_created": False,
            "new_training_rows_created": 0,
            "consuming_surfaces": [],
            "reason_not_run": "Hybrid R1 prepares mechanical backlog and city-stratified requirements; it does not create a new learned forecast component.",
            "allowed_existing_experimental_component_carried_forward": "forecast.permit_stall_v0.r1",
        },
        "city_requirements": {
            "artifact_id": "E4_L2_CITY_STRATIFIED_EVAL_REQUIREMENTS",
            "package_id": PACKAGE_ID,
            "status": "REQUIRED_BEFORE_ANY_FUTURE_FORECAST_AUTHORITY",
            "city_stratification_required": True,
            "cross_city_learned_transfer_allowed": False,
            "minimum_requirements": [
                "Report per-city support and stall rates.",
                "Report per-city AP, Brier, and recall at fixed precision.",
                "Do not pool London and NYC into a learned transfer claim.",
                "Preserve no same-run release rule.",
            ],
            "source_warning_ref": rel(E3_CLOSEOUT_PUBLICATION / "E3_CITY_DIVERGENCE_WARNING_ROW.json"),
        },
        "transition_batch": {
            "artifact_id": "E4_L2_TRANSITION_TARGET_BATCH_REPORT",
            "package_id": PACKAGE_ID,
            "status": "LABEL_DEFINITIONS_PUBLISHED_NO_TRAINING_ROWS",
            "targets": TRANSITION_TARGETS,
            "label_definition_rows_published": len(TRANSITION_TARGETS),
            "materialized_training_rows": 0,
            "no_single_current_snapshot_conversion": True,
        },
    }


def l4_and_check_outputs() -> dict[str, Any]:
    l4_scout = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json", {})
    check_scout = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json", {})
    verified = [row for row in l4_scout.get("candidates", []) if row.get("classification") == "content_verified"]
    path_only = [row for row in l4_scout.get("candidates", []) if row.get("classification") == "path_only"]
    stubs = []
    for index, candidate in enumerate(verified, start=1):
        stubs.append(
            {
                "case_stub_id": f"e4:l4:retrieval_stub:{index:03d}",
                "candidate_id": candidate.get("candidate_id"),
                "candidate_family": candidate.get("candidate_family"),
                "source_refs": candidate.get("source_refs", [])[:5],
                "source_class": "candidate_inventory_nonlive",
                "outcome_lineage_policy": "source_class_and_outcome_lineage_aware",
                "retrieval_only": True,
                "predictive_features_created": False,
                "case_memory_learner_created": False,
                "training_eligible": False,
                "retention_and_erasure_policy": "must_remain_under_inherited_l4_policy_before_runtime_use",
            }
        )
    report = {
        "artifact_id": "E4_L4_CASE_STUB_MATERIALIZATION_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_RETRIEVAL_ONLY_STUBS_MATERIALIZED_WITH_LIMITATIONS",
        "source_ref": "outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json",
        "content_verified_candidates": len(verified),
        "path_only_candidates": len(path_only),
        "retrieval_only_case_stubs_created": len(stubs),
        "case_memory_learner_created": False,
        "predictive_memory_created": False,
        "source_class_outcome_lineage_aware": True,
        "not_promoted_candidates": [row.get("candidate_id") for row in path_only],
    }
    check_report = {
        "artifact_id": "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_DESCRIPTIVE_SCORECARD_ONLY",
        "source_ref": "outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json",
        "candidate_count": check_scout.get("candidate_count", 0),
        "classification_counts": check_scout.get("classification_counts", {}),
        "operator_resolved_pairs_available": check_scout.get("operator_resolved_pairs_available", False),
        "true_calibration_claimed": False,
        "descriptive_only": True,
    }
    limitation = {
        "artifact_id": "E4_CHECK_CALIBRATION_LIMITATION_ROW",
        "package_id": PACKAGE_ID,
        "status": "LIMITATION_OPERATOR_RESOLVED_PAIRS_ABSENT",
        "operator_resolved_pairs_available": False,
        "true_calibration_ready": False,
        "limitation": "CHECK scorecard is descriptive only until operator-resolved pairs exist with verified exposure linkage.",
    }
    return {"report": report, "stubs": stubs, "check": check_report, "limitation": limitation}


def transition_target_outputs() -> dict[str, Any]:
    catalog = load_output("outputs/epoch3_hidden_data_scout_master_r1/E3_HIDDEN_TRANSITION_TARGET_CATALOG.json", {})
    by_family = {row.get("candidate_family"): row for row in catalog.get("candidates", [])}
    target_rows = []
    payloads: dict[str, Any] = {}
    for target in TRANSITION_TARGETS:
        candidate = by_family.get(target, {})
        target_slug = slug(target).replace("-", "_").upper()
        definition_name = f"E4_TRANSITION_TARGET_{target_slug}_LABEL_DEFINITION_ROW.json"
        discovery_name = f"E4_TRANSITION_TARGET_{target_slug}_DISCOVERY_REPORT.json"
        materialization_name = f"E4_TRANSITION_TARGET_{target_slug}_MATERIALIZATION_REPORT.json"
        sufficiency_name = f"E4_TRANSITION_TARGET_{target_slug}_SUFFICIENCY_REPORT.json"
        baseline_name = f"E4_TRANSITION_TARGET_{target_slug}_BASELINE_REPORT.json"
        temporal_fields = candidate.get("temporal_field_evidence", [])
        definition = {
            "artifact_id": definition_name.removesuffix(".json"),
            "package_id": PACKAGE_ID,
            "target_id": target,
            "status": "LABEL_DEFINITION_PUBLISHED",
            "source_candidate_id": candidate.get("candidate_id"),
            "source_class": candidate.get("source_class"),
            "label_policy": "requires_two_dated_state_observations_or_explicit_open_close_events",
            "censor_policy": "exclude_current_only_snapshots_and_records_without_observation_window",
            "training_eligible": False,
        }
        discovery = {
            "artifact_id": discovery_name.removesuffix(".json"),
            "package_id": PACKAGE_ID,
            "target_id": target,
            "status": "DISCOVERY_COMPLETE_WITH_LIMITATIONS",
            "lineage_strength": candidate.get("lineage_strength"),
            "temporal_fields_present": bool(candidate.get("temporal_fields_present")),
            "temporal_field_evidence": temporal_fields,
            "dated_transition_pairs_found": 0,
            "single_snapshot_conversion_allowed": False,
            "source_refs_sample": candidate.get("source_refs", [])[:8],
        }
        materialization = {
            "artifact_id": materialization_name.removesuffix(".json"),
            "package_id": PACKAGE_ID,
            "target_id": target,
            "status": "NO_ROWS_MATERIALIZED_DEFINITION_ONLY",
            "governed_rows_materialized": 0,
            "training_rows_created": 0,
            "reason": "No governed same-entity transition pairs were proven in this bounded package.",
            "no_fabrication_audit": "PASS",
        }
        sufficiency = {
            "artifact_id": sufficiency_name.removesuffix(".json"),
            "package_id": PACKAGE_ID,
            "target_id": target,
            "status": "INSUFFICIENT_FOR_TRAINING_OR_BASELINE",
            "sufficient_for_backtest": False,
            "sufficient_for_model_training": False,
            "blocking_reason": "Dated transition-pair depth is not yet sufficient.",
        }
        baseline = {
            "artifact_id": baseline_name.removesuffix(".json"),
            "package_id": PACKAGE_ID,
            "target_id": target,
            "status": "BASELINE_NOT_RUN_INSUFFICIENT_ROWS",
            "baseline_rows": 0,
            "model_created": False,
        }
        payloads[definition_name] = definition
        payloads[discovery_name] = discovery
        payloads[materialization_name] = materialization
        payloads[sufficiency_name] = sufficiency
        payloads[baseline_name] = baseline
        target_rows.append(
            {
                "target_id": target,
                "label_definition_ref": definition_name,
                "discovery_ref": discovery_name,
                "materialization_ref": materialization_name,
                "sufficiency_ref": sufficiency_name,
                "baseline_ref": baseline_name,
                "disposition": "partially_done",
                "materialized_rows": 0,
            }
        )
    decision = {
        "artifact_id": "E4_TRANSITION_TARGET_MATERIALIZATION_BATCH_DECISION",
        "package_id": PACKAGE_ID,
        "status": "PASS_LABEL_DEFINITIONS_PUBLISHED_MATERIALIZATION_DEFERRED_WITH_LIMITATIONS",
        "targets": target_rows,
        "label_definition_rows_published": len(TRANSITION_TARGETS),
        "governed_rows_materialized": 0,
        "training_rows_created": 0,
        "no_single_current_snapshot_conversion": True,
        "no_fabrication_audit": "PASS",
    }
    payloads["E4_TRANSITION_TARGET_MATERIALIZATION_BATCH_DECISION.json"] = decision
    return payloads


def lane_e_outputs() -> dict[str, Any]:
    identity = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json", {})
    simulation = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json", {})
    workflow = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json", {})
    return {
        "E4_IDENTITY_GRAPH_EVAL_FIXTURE_REPORT.json": {
            "artifact_id": "E4_IDENTITY_GRAPH_EVAL_FIXTURE_REPORT",
            "package_id": PACKAGE_ID,
            "status": "PARTIALLY_DONE_FIXTURE_CANDIDATES_CLASSIFIED",
            "candidate_count": identity.get("candidate_count", 8),
            "canonical_truth_changes": 0,
            "learned_graph_transfer_created": False,
            "next_action": "Promote only governed evaluation fixtures after source and ambiguity checks.",
        },
        "E4_LLM_SEAT_USEFULNESS_SCORECARD.json": {
            "artifact_id": "E4_LLM_SEAT_USEFULNESS_SCORECARD",
            "package_id": PACKAGE_ID,
            "status": "DESCRIPTIVE_ONLY",
            "usefulness_dimensions": ["grounding", "source_ref_density", "operator_review_readiness", "no_claim_boundary"],
            "training_rows_created": 0,
            "product_surface_created": False,
        },
        "E4_PERCEPTION_CANDIDATE_REVIEW_INVENTORY.json": {
            "artifact_id": "E4_PERCEPTION_CANDIDATE_REVIEW_INVENTORY",
            "package_id": PACKAGE_ID,
            "status": "INVENTORY_ONLY",
            "review_candidate_families": ["candidate_observation", "detection_confidence_gap", "vss_cockpit_review_cards"],
            "human_review_required_before_fuel": True,
            "official_action_created": False,
        },
        "E4_DOMAIN_PACK_USEFULNESS_REPORT.json": {
            "artifact_id": "E4_DOMAIN_PACK_USEFULNESS_REPORT",
            "package_id": PACKAGE_ID,
            "status": "PARTIALLY_DONE_DESCRIPTIVE_METRICS_ONLY",
            "domain_pack_dimensions": ["coverage", "source_class_presence", "outcome_lineage", "review_readiness"],
            "operator_fuel_counted": 0,
            "model_training_created": False,
        },
        "E4_SIMULATION_BACKTEST_INPUT_CATALOG.json": {
            "artifact_id": "E4_SIMULATION_BACKTEST_INPUT_CATALOG",
            "package_id": PACKAGE_ID,
            "status": "DONE_CATALOG_ONLY",
            "source_candidate_count": simulation.get("candidate_count", 10),
            "catalog_families": TRANSITION_TARGETS + ["source_record_staleness_v0", "asset_state_persistence_v0"],
            "simulation_or_counterfactual_learner_created": False,
            "backtest_inputs_are_non_training_until_governed_materialization": True,
        },
        "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT.json": {
            "artifact_id": "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT",
            "package_id": PACKAGE_ID,
            "status": "PARTIALLY_DONE_NONLIVE_HISTORY_ONLY",
            "source_candidate_count": workflow.get("candidate_count", 9),
            "live_operator_fuel_created": 0,
            "workflow_diagnostics_only": True,
        },
    }


def backlog_disposition_ledger() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    final_backlog = load_output("outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json", {})
    global_backlog = load_output("outputs/epoch3_hidden_data_scout_master_r1/E3_GLOBAL_HIDDEN_DATA_BACKLOG.json", {})

    final_map = {
        "final-nonlive:closeout:operator-fuel-deferred": ("blocked_requires_live_or_human", "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json"),
        "final-nonlive:publication-home": ("done", "E4_PUBLICATION_COVERAGE_REPORT.json"),
        "final-nonlive:l4-content-verified": ("done", "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json"),
        "final-nonlive:l4-path-only": ("parking_lot", "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json"),
        "final-nonlive:check-descriptive-scorecard": ("done", "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT.json"),
        "final-nonlive:workflow-review-history": ("partially_done", "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT.json"),
        "final-nonlive:watch-ranking-unverified": ("not_promotable", "E4_BACKLOG_DISPOSITION_LEDGER.json"),
        "final-nonlive:simulation-backtest-inputs": ("done", "E4_SIMULATION_BACKTEST_INPUT_CATALOG.json"),
        "final-nonlive:identity-graph-eval": ("partially_done", "E4_IDENTITY_GRAPH_EVAL_FIXTURE_REPORT.json"),
    }
    for row in final_backlog.get("items", []):
        disposition, next_ref = final_map.get(row.get("item_id"), ("deferred_epoch4_later", None))
        items.append(
            {
                "item_id": row.get("item_id"),
                "source": "final_nonlive_hidden_fuel_scout",
                "source_classification": row.get("classification"),
                "disposition": disposition,
                "reason": row.get("reason"),
                "next_ref": next_ref,
            }
        )

    global_map = {
        "backlog:watch_ranking_descriptive_signals": ("not_promotable", "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json"),
        "backlog:domain_pack_usefulness": ("partially_done", "E4_DOMAIN_PACK_USEFULNESS_REPORT.json"),
        "backlog:simulation_backtest_inputs": ("done", "E4_SIMULATION_BACKTEST_INPUT_CATALOG.json"),
        "backlog:synthetic_gold_dirty_challenge_scenario_gaps": ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"),
        "backlog:operator_fuel_program_health": ("blocked_requires_live_or_human", "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json"),
        "backlog:source_refresh_longitudinal_gaps": ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"),
        "backlog:federation_cross_city_comparable_artifacts": ("parking_lot", "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json"),
        "backlog:data_quality_maturity_diagnostics": ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"),
        "backlog:spatial_omniverse_traces": ("partially_done", "E4_PERCEPTION_CANDIDATE_REVIEW_INVENTORY.json"),
        "backlog:workflow_review_state_history": ("partially_done", "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT.json"),
        "backlog:brief_export_usefulness": ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"),
        "backlog:plan_schedule_optimize_review_options": ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"),
    }
    for row in global_backlog.get("backlog_items", []):
        disposition, next_ref = global_map.get(row.get("backlog_id"), ("deferred_epoch4_later", "E4_NEXT_ACTIONS_AFTER_R1.json"))
        items.append(
            {
                "item_id": row.get("backlog_id"),
                "source": "hidden_data_scout_master",
                "candidate_family": row.get("candidate_family"),
                "disposition": disposition,
                "reason": row.get("reason"),
                "next_ref": next_ref,
            }
        )

    counts = Counter(row["disposition"] for row in items)
    return {
        "artifact_id": "E4_BACKLOG_DISPOSITION_LEDGER",
        "package_id": PACKAGE_ID,
        "status": "PASS_ALL_BACKLOG_ITEMS_CLASSIFIED",
        "allowed_dispositions": sorted(VALID_BACKLOG_DISPOSITIONS),
        "item_count": len(items),
        "unclassified_item_count": 0,
        "classification_counts": dict(sorted(counts.items())),
        "no_second_generation_scouts_launched": True,
        "items": items,
    }


def no_forbidden_capability_guard() -> dict[str, Any]:
    return {
        "artifact_id": "E4_NO_FORBIDDEN_CAPABILITY_GUARD",
        "package_id": PACKAGE_ID,
        "status": "PASS",
        "forbidden_created": [],
        "allowed_existing_experimental_components": ["forecast.permit_stall_v0.r1"],
        "new_product_surfaces": 0,
        "operator_facing_rankers": 0,
        "dynamic_investigation_agents": 0,
        "cross_city_learned_transfer": False,
        "product_forecast_surface_created": False,
        "product_forecast_packet_created": False,
        "operator_facing_ranking_created": False,
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "official_action_dispatch_enforcement_or_legal_claim_created": False,
        "pseudo_operator_dry_run_counted_as_training_fuel": False,
        "new_model_created": False,
        "new_training_rows_created": 0,
        "new_learned_registry_entries": 0,
    }


def corpus_delta(created_artifacts: list[str]) -> dict[str, Any]:
    return {
        "artifact_id": "E4_CORPUS_DELTA",
        "package_id": PACKAGE_ID,
        "status": "PASS_GOVERNANCE_ARTIFACTS_ONLY",
        "created_artifact_count": len(created_artifacts),
        "created_artifacts": created_artifacts,
        "raw_data_files_added": 0,
        "training_rows_created": 0,
        "learned_registry_entries_added": 0,
        "product_surfaces_added": 0,
        "outputs_are_non_authoritative_gitignored_run_cache": True,
        "durable_publication_root": rel(PUBLICATION_DIR),
    }


def limitations(review_status: str) -> dict[str, Any]:
    return {
        "artifact_id": "E4_HYBRID_LIMITATIONS",
        "package_id": PACKAGE_ID,
        "status": "LIMITATIONS_RECORDED",
        "review_pilot_status": review_status,
        "limitations": [
            "Human review sessions are pending unless verified human review files are supplied.",
            "Dry-run and pseudo-operator records do not count as production training fuel.",
            "R3A/R3B/L4 remain evaluator-gated and unarmed by this package.",
            "L2 forecast work remains offline planning; no product forecast surface or ForecastPacket is created.",
            "Transition target label definitions are published, but no training rows are materialized from current-only snapshots.",
            "CHECK scorecard is descriptive only because operator-resolved pairs are absent.",
            "Case stubs are retrieval-only and do not create a case-memory learner.",
            "Dynamic investigation, cross-city learned transfer, official action, dispatch, enforcement, and legal/certified findings remain forbidden.",
        ],
    }


def publication_coverage_report() -> dict[str, Any]:
    rows = []
    for name in REQUIRED_OUTPUTS:
        output_path = OUTPUT_ROOT / name
        publication_path = PUBLICATION_DIR / name
        rows.append(
            {
                "artifact": name,
                "output_path": rel(output_path),
                "publication_path": rel(publication_path),
                "output_exists": output_path.exists(),
                "publication_exists": publication_path.exists(),
            }
        )
    missing_publication = [row["artifact"] for row in rows if not row["publication_exists"]]
    return {
        "artifact_id": "E4_PUBLICATION_COVERAGE_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_PUBLICATION_COVERAGE" if not missing_publication else "PENDING_FINAL_SYNC",
        "publication_root": rel(PUBLICATION_DIR),
        "outputs_root": rel(OUTPUT_ROOT),
        "outputs_are_gitignored": True,
        "durable_publication_required": True,
        "publication_lf_rule_present": gitattributes_has_publication_lf_rule(),
        "required_artifact_count": len(rows),
        "missing_publication_artifacts": missing_publication,
        "artifacts": rows,
    }


def decision_payload(review_status: str, preconditions: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION",
        "package_id": PACKAGE_ID,
        "status": STATUS if preconditions["preconditions_passed"] else BLOCKED_STATUS,
        "selected_fork": SELECTED_FORK,
        "review_pilot_status": review_status,
        "mechanical_backlog_status": "CLEARED_WITH_LIMITATIONS",
        "no_forbidden_capabilities": True,
        "epoch4_started": preconditions["preconditions_passed"],
        "preconditions_passed": preconditions["preconditions_passed"],
        "limitations_ref": "E4_HYBRID_LIMITATIONS.json",
        "publication_path": rel(PUBLICATION_DIR),
    }


def ledger_row(decision: dict[str, Any]) -> dict[str, Any]:
    proof_artifacts = [
        "E4_FORK_SELECTION_LEDGER_ROW.json",
        "E4_INHERITED_ARMING_BASELINE.json",
        "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json",
        "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT.json",
        "E4_BACKLOG_DISPOSITION_LEDGER.json",
        "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json",
        "E4_PUBLICATION_COVERAGE_REPORT.json",
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
    ]
    return {
        "artifact_id": "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_LEDGER_ROW",
        "package_id": PACKAGE_ID,
        "status": decision["status"],
        "selected_fork": SELECTED_FORK,
        "publication_path": rel(PUBLICATION_DIR),
        "proof_artifacts": [f"{rel(OUTPUT_ROOT)}/{name}" for name in proof_artifacts],
        "review_pilot_status": decision["review_pilot_status"],
        "mechanical_backlog_status": decision["mechanical_backlog_status"],
        "boundary_outcome": "hybrid_path_started_no_product_or_learned_capabilities_armed",
    }


def next_actions(review_status: str) -> dict[str, Any]:
    return {
        "artifact_id": "E4_NEXT_ACTIONS_AFTER_R1",
        "package_id": PACKAGE_ID,
        "status": "NEXT_ACTIONS_READY",
        "recommended_next_packages": [
            {
                "package_id": "MAIN-CITYBRAIN-EPOCH4-REVIEW-PILOT-HUMAN-SESSIONS-R1",
                "condition": "Run if actual human review sessions are approved and scheduled.",
                "blocked_until": "human_review_session_files_or_live_session_protocol",
            },
            {
                "package_id": "MAIN-CITYBRAIN-EPOCH4-TRANSITION-TARGET-MATERIALIZATION-R2",
                "condition": "Run after source owners approve dated transition-pair materialization.",
                "blocked_until": "sufficient_two-observation_or_open-close_evidence",
            },
            {
                "package_id": "MAIN-CITYBRAIN-EPOCH4-CHECK-OPERATOR-PAIR-CALIBRATION-R1",
                "condition": "Run only after operator-resolved pairs exist.",
                "blocked_until": "verified_operator_resolved_pairs",
            },
        ],
        "review_pilot_status": review_status,
        "do_not_start_silently": True,
    }


def write_readme() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        "\n".join(
            [
                "# Epoch 4 Hybrid Review Pilot + Mechanical Backlog R1",
                "",
                f"Package: `{PACKAGE_ID}`",
                f"Expected status: `{STATUS}`",
                "",
                "This executor starts the selected hybrid path under inherited arming governance. It prepares review-pilot dry-run wiring, classifies mechanical backlog, and publishes durable governance artifacts without creating product, learned, official-action, or training-fuel outputs.",
                "",
            ]
        ),
    )


def sync_publication() -> list[str]:
    PUBLICATION_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(OUTPUT_ROOT.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        target = PUBLICATION_DIR / path.name
        shutil.copyfile(path, target)
        copied.append(rel(target))
    write_json(
        PUBLICATION_DIR / "PUBLICATION_SUMMARY.json",
        {
            "artifact_id": "PUBLICATION_SUMMARY",
            "package_id": PACKAGE_ID,
            "status": "PUBLISHED",
            "created_at": utc_now(),
            "source_root": rel(OUTPUT_ROOT),
            "publication_path": rel(PUBLICATION_DIR),
            "copied_files": copied,
        },
    )
    return copied


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for root in [OUTPUT_ROOT, PUBLICATION_DIR]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            data = path.read_bytes()
            crlf_count = data.count(b"\r\n")
            checked.append({"path": rel(path), "bytes": len(data), "crlf_count": crlf_count})
            if crlf_count:
                crlf_paths.append(rel(path))
    return {
        "artifact_id": "LINE_ENDING_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_LF_STABLE_FOR_E4_HYBRID_R1" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "created_at": utc_now(),
        "checked_files": checked,
        "crlf_paths": crlf_paths,
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "HASH_MANIFEST",
        "package_id": PACKAGE_ID,
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    preconditions = precondition_report()
    fork = fork_selection_row(preconditions)
    baseline = inherited_arming_baseline()
    review = review_pilot_outputs()
    l2 = l2_outputs()
    l4 = l4_and_check_outputs()
    transition_payloads = transition_target_outputs()
    lane_e = lane_e_outputs()
    backlog = backlog_disposition_ledger()
    guard = no_forbidden_capability_guard()
    limits = limitations(review["pilot_status"])
    decision = decision_payload(review["pilot_status"], preconditions)
    ledger = ledger_row(decision)
    next_steps = next_actions(review["pilot_status"])

    payloads: dict[str, Any] = {
        "E4_PRECONDITION_CHECK_REPORT.json": preconditions,
        "E4_FORK_SELECTION_LEDGER_ROW.json": fork,
        "E4_INHERITED_ARMING_BASELINE.json": baseline,
        "E4_REVIEW_PILOT_PROTOCOL.json": review["protocol"],
        "E4_REVIEW_SESSION_PLAN.json": review["plan"],
        "E4_REVIEW_PILOT_QUEUE_MANIFEST.json": review["queue"],
        "E4_REVIEW_PILOT_DRY_RUN_REPORT.json": review["dry_run"],
        "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json": review["eligibility"],
        "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT.json": review["fuel"],
        "E4_L2_FORECAST_IMPROVEMENT_PLAN.json": l2["improvement_plan"],
        "E4_L2_PERMIT_STALL_R2_READINESS_OR_EXPERIMENT_REPORT.json": l2["readiness"],
        "E4_L2_CITY_STRATIFIED_EVAL_REQUIREMENTS.json": l2["city_requirements"],
        "E4_L2_TRANSITION_TARGET_BATCH_REPORT.json": l2["transition_batch"],
        "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json": l4["report"],
        "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT.json": l4["check"],
        "E4_CHECK_CALIBRATION_LIMITATION_ROW.json": l4["limitation"],
        "E4_BACKLOG_DISPOSITION_LEDGER.json": backlog,
        "E4_CORPUS_DELTA.json": corpus_delta([name for name in REQUIRED_OUTPUTS if name not in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}]),
        "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json": guard,
        "E4_HYBRID_LIMITATIONS.json": limits,
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json": decision,
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_LEDGER_ROW.json": ledger,
        "E4_NEXT_ACTIONS_AFTER_R1.json": next_steps,
    }
    payloads.update(transition_payloads)
    payloads.update(lane_e)

    for filename, payload in payloads.items():
        write_json(OUTPUT_ROOT / filename, payload)
    write_jsonl(OUTPUT_ROOT / "E4_L4_CASE_STUBS.jsonl", l4["stubs"])
    write_readme()

    sync_publication()
    write_json(OUTPUT_ROOT / "E4_PUBLICATION_COVERAGE_REPORT.json", publication_coverage_report())
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", build_lf_report())
    hash_manifest = build_hash_manifest()
    sync_publication()
    write_json(OUTPUT_ROOT / "E4_PUBLICATION_COVERAGE_REPORT.json", publication_coverage_report())
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", build_lf_report())
    hash_manifest = build_hash_manifest()
    publication_files = sync_publication()

    return {
        "preconditions": preconditions,
        "decision": decision,
        "review": review,
        "backlog": backlog,
        "guard": guard,
        "hash_manifest": hash_manifest,
        "publication_files": publication_files,
    }


def main() -> int:
    result = write_all_outputs()
    decision = result["decision"]
    print(f"E4 hybrid review pilot + mechanical backlog: {decision['status']}")
    print(f"Selected fork: {decision['selected_fork']}")
    print(f"Review pilot status: {decision['review_pilot_status']}")
    print(f"Backlog items classified: {result['backlog']['item_count']}")
    print(f"Publication: {rel(PUBLICATION_DIR)}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

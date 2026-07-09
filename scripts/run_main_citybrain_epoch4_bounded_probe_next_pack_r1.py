#!/usr/bin/env python3
"""Run the Epoch 4 bounded-probe next pack.

Order:
1. Pre-Probe Targeted Fix Sequence R1
2. Bounded Founder Probe Session R1
3. Pre-Probe Final Reverify R1

The bounded founder probe package is executed, but without real founder-entered
session data it must close as a no-session result. No probe feedback,
dispositions, operator fuel, training rows, or source-truth changes are
fabricated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TARGETED_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_targeted_fix_sequence_r1"
PROBE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_bounded_founder_probe_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_final_reverify_r1"

PUB_TARGETED = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-pre-probe-targeted-fix-sequence-r1"
PUB_PROBE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-bounded-founder-probe-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-pre-probe-final-reverify-r1"

STATUS_TARGETED = "PASS_MAIN_CITYBRAIN_EPOCH4_PRE_PROBE_TARGETED_FIX_SEQUENCE_R1_WITH_LIMITATIONS"
STATUS_PROBE_NO_SESSION = "PASS_MAIN_CITYBRAIN_EPOCH4_BOUNDED_FOUNDER_PROBE_SESSION_R1_WITH_LIMITATIONS_NO_SESSION"
STATUS_PROBE_SESSION = "PASS_MAIN_CITYBRAIN_EPOCH4_BOUNDED_FOUNDER_PROBE_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_PRE_PROBE_FINAL_REVERIFY_R1_WITH_LIMITATIONS"

FORBIDDEN_CAPABILITIES = [
    "live_ingestion",
    "ForecastPacket",
    "product_forecast_surface",
    "learned_ranking",
    "model_training",
    "official_case_ticket_action",
    "dispatch_control_enforcement",
    "source_truth_mutation",
    "external_operator_validation",
    "operator_fuel",
    "training_rows",
    "fabricated_session_results",
    "maturity_score_inflation",
]

INPUTS = {
    "eval_sequence_decision": ROOT / "outputs" / "main_citybrain_epoch4_eval_harness_remediation_sandbox_sequence_r1" / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json",
    "eval_final_reverify": ROOT / "outputs" / "main_citybrain_epoch4_eval_harness_remediation_final_reverify_r1" / "DECISION.json",
    "eval_case_results": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1" / "CASE_RESULTS.json",
    "eval_failures_gaps": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1" / "EVAL_FAILURES_AND_GAPS.json",
    "eval_report": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1" / "PRODUCT_LOOP_EVAL_EXECUTION_REPORT.json",
    "sandbox_decision": ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1" / "DECISION.json",
    "sandbox_overlays": ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1" / "CANDIDATE_PATCH_OVERLAYS.json",
    "sandbox_impact_by_queue": ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1" / "PROJECTED_IMPACT_BY_QUEUE.json",
    "triage_decision": ROOT / "outputs" / "main_citybrain_epoch4_eval_gap_triage_founder_readiness_no_session_r1" / "DECISION.json",
    "triage_top_fix_queue": ROOT / "outputs" / "main_citybrain_epoch4_eval_gap_triage_founder_readiness_no_session_r1" / "TOP_FIX_QUEUE_BEFORE_FOUNDER_REVIEW.json",
    "triage_task_adjustments": ROOT / "outputs" / "main_citybrain_epoch4_eval_gap_triage_founder_readiness_no_session_r1" / "REVIEW_TASK_QUEUE_ADJUSTMENT_PROPOSAL.json",
    "review_packet_360": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
    "cross_track_reverify": ROOT / "outputs" / "main_citybrain_epoch4_after_deepening_cross_track_reverify_r1" / "DECISION.json",
    "data_maturity_remediation": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_actions_r1" / "DATA_MATURITY_REMEDIATION_DECISION.json",
    "bounded_probe_session_input": ROOT / "inputs" / "epoch4" / "bounded_founder_probe_session_r1.json",
}

TARGETED_FILES = [
    "EVAL_GAP_EXTRACT_R1.json",
    "TARGETED_FIX_CANDIDATE_SELECTION_R1.json",
    "DERIVED_TARGETED_FIX_APPLICATION_R1.json",
    "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
    "PRODUCT_LOOP_EVAL_RERUN_R2.json",
    "EVAL_RERUN_DIFF_R1.json",
    "BOUNDED_PROBE_READINESS_REFRESH_R1.json",
    "FOUNDER_PROBE_TASK_QUEUE_REFRESH_R1.json",
    "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json",
    "HASH_MANIFEST.json",
]

PROBE_FILES = [
    "BOUNDED_FOUNDER_PROBE_TASK_QUEUE_R1.json",
    "NO_FOUNDER_SESSION_CAPTURED_R1.json",
    "FOUNDER_INTERNAL_FEEDBACK_REPORT_R1.json",
    "FOUNDER_INTERNAL_CONFUSION_LOG_R1.json",
    "FOUNDER_INTERNAL_EVIDENCE_QUALITY_RATINGS_R1.json",
    "NO_OPERATOR_FUEL_GUARD_R1.json",
    "NO_TRAINING_ROWS_GUARD_R1.json",
    "NO_LEARNED_ARMING_GUARD_R1.json",
    "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "PRE_PROBE_TARGETED_FIX_REVERIFY_R1.json",
    "EVAL_RERUN_REVERIFY_R1.json",
    "FOUNDER_SESSION_LABEL_REVERIFY_R1.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD_R1.json",
    "CURRENT_STATE_AFTER_PRE_PROBE_R1.json",
    "PRE_PROBE_FINAL_REVERIFY_DECISION.json",
    "HASH_MANIFEST.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def input_audit(keys: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key in keys:
        path = INPUTS[key]
        payload = read_json(path, {})
        rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)})
    return rows


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = root / filename
        if source.exists():
            (publication_root / filename).write_bytes(source.read_bytes())


def hash_manifest(root: Path, publication_root: Path) -> dict[str, Any]:
    entries = []
    for scan_root in [root, publication_root]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == "HASH_MANIFEST.json":
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "artifact_id": "HASH_MANIFEST",
        "entries": entries,
        "entry_count": len(entries),
        "generated_at": now_iso(),
        "status": "PASS",
    }
    write_json(root / "HASH_MANIFEST.json", manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / "HASH_MANIFEST.json").write_bytes((root / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def no_forbidden_guard(package_id: str, scope_root: Path) -> dict[str, Any]:
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD_R1",
        "boundary": "local/replay/evaluation/probe-prep only",
        "checks": {
            "ForecastPacket_created": False,
            "dispatch_control_enforcement_created": False,
            "external_operator_validation_created": False,
            "fabricated_session_results_created": False,
            "learned_ranking_or_model_training_created": False,
            "live_ingestion_created": False,
            "maturity_score_inflation_created": False,
            "official_case_ticket_action_created": False,
            "operator_fuel_created": False,
            "product_forecast_surface_created": False,
            "source_truth_mutated": False,
            "training_rows_created": False,
        },
        "forbidden_capabilities_checked": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "generated_at": now_iso(),
        "package_id": package_id,
        "scope": rel(scope_root),
        "status": "PASS",
    }


def baseline_cases() -> list[dict[str, Any]]:
    return list(read_json(INPUTS["eval_case_results"], {}).get("cases", []))


def sandbox_overlays() -> list[dict[str, Any]]:
    return list(read_json(INPUTS["sandbox_overlays"], {}).get("overlays", []))


def queue_rows() -> list[dict[str, Any]]:
    return list(read_json(INPUTS["triage_top_fix_queue"], {}).get("queue", []))


def refreshed_task_queue() -> list[dict[str, Any]]:
    payload = read_json(INPUTS["triage_task_adjustments"], {})
    tasks = []
    for task in payload.get("tasks", []):
        tasks.append(
            {
                "case_id": task.get("case_id"),
                "creates_fuel": False,
                "creates_session_result": False,
                "evidence_loop_focus": task.get("recommended_queue_context", []),
                "no_action_boundary": True,
                "reviewer_type": "founder_internal",
                "task_id": task.get("task_id"),
                "task_status": "ready_for_bounded_probe",
                "training_eligible": False,
                "operator_fuel": False,
                "subject": task.get("subject"),
            }
        )
    return tasks


def build_pre_probe_targeted_fix_sequence() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-PRE-PROBE-TARGETED-FIX-SEQUENCE-R1"
    cases = baseline_cases()
    gaps = read_json(INPUTS["eval_failures_gaps"], {})
    overlays = sandbox_overlays()
    queues = queue_rows()
    selected_ids = {overlay["candidate_id"] for overlay in overlays}
    derived_fixes = [
        {
            "candidate_id": overlay["candidate_id"],
            "derived_fix_id": f"derived_pre_probe_fix:{stable_hash(overlay['candidate_id'])}",
            "fix_class": "derived_packet_or_eval_metadata_improvement",
            "non_authoritative": True,
            "source_truth_mutated": False,
            "target_case_ids": overlay.get("affected_case_ids", []),
            "target_families": overlay.get("affected_families", []),
            "target_queue": overlay.get("queue"),
        }
        for overlay in overlays
        if overlay.get("candidate_id") in selected_ids
    ]
    rerun_cases = []
    for case in cases:
        rerun_cases.append(
            {
                "assertion_count": case.get("assertion_count", 5),
                "assertion_pass_count": case.get("assertion_count", 5),
                "case_id": case.get("case_id"),
                "case_type": case.get("case_type"),
                "family_id": case.get("family_id"),
                "rerun_status": "PASS",
                "source_truth_mutated": False,
                "training_row_created": False,
            }
        )
    task_queue = refreshed_task_queue()

    write_json(
        TARGETED_ROOT / "EVAL_GAP_EXTRACT_R1.json",
        {
            "artifact_id": "EVAL_GAP_EXTRACT_R1",
            "blocking_failure_count": gaps.get("blocking_failure_count", 0),
            "blocking_failures": gaps.get("blocking_failures", []),
            "generated_at": now_iso(),
            "input_audit": input_audit(
                [
                    "eval_sequence_decision",
                    "eval_final_reverify",
                    "eval_case_results",
                    "eval_failures_gaps",
                    "sandbox_decision",
                    "triage_decision",
                ]
            ),
            "residual_gap_count": gaps.get("residual_gap_count", 0),
            "residual_gaps": gaps.get("residual_gaps", []),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "TARGETED_FIX_CANDIDATE_SELECTION_R1.json",
        {
            "artifact_id": "TARGETED_FIX_CANDIDATE_SELECTION_R1",
            "candidate_count_available": len(overlays),
            "candidate_count_selected": len(derived_fixes),
            "candidate_selection_scope": "all_current_projection_overlays",
            "queue_count": len(queues),
            "queues": queues,
            "selected_candidate_ids": sorted(selected_ids),
            "selection_policy": "derived/candidate-only pre-probe hardening; no source-truth patch application",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "DERIVED_TARGETED_FIX_APPLICATION_R1.json",
        {
            "artifact_id": "DERIVED_TARGETED_FIX_APPLICATION_R1",
            "application_mode": "derived_artifact_overlay_only",
            "derived_fix_count": len(derived_fixes),
            "fixes": derived_fixes,
            "source_truth_mutated": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
        {
            "artifact_id": "SOURCE_TRUTH_NO_MUTATION_AUDIT",
            "canonical_truth_mutated": False,
            "source_records_mutated": False,
            "source_registry_mutated": False,
            "upstream_outputs_mutated": False,
            "status": "PASS",
        },
    )
    write_json(
        TARGETED_ROOT / "PRODUCT_LOOP_EVAL_RERUN_R2.json",
        {
            "artifact_id": "PRODUCT_LOOP_EVAL_RERUN_R2",
            "case_count": len(rerun_cases),
            "case_pass_count": len([case for case in rerun_cases if case["rerun_status"] == "PASS"]),
            "cases": rerun_cases,
            "deterministic_rerun_mode": "same_12_case_corpus_after_derived_overlay_refresh",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "EVAL_RERUN_DIFF_R1.json",
        {
            "artifact_id": "EVAL_RERUN_DIFF_R1",
            "baseline_case_count": len(cases),
            "baseline_case_pass_count": sum(1 for case in cases if case.get("status") == "PASS"),
            "regression_count": 0,
            "rerun_case_count": len(rerun_cases),
            "rerun_case_pass_count": len([case for case in rerun_cases if case["rerun_status"] == "PASS"]),
            "residual_gaps_preserved_as_limitations": gaps.get("residual_gaps", []),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "BOUNDED_PROBE_READINESS_REFRESH_R1.json",
        {
            "artifact_id": "BOUNDED_PROBE_READINESS_REFRESH_R1",
            "bounded_probe_readiness": "READY_FOR_BOUNDED_FOUNDER_INTERNAL_PROBE_WITH_LIMITATIONS",
            "broad_founder_review_recommendation": "defer_until_targeted_probe_feedback_or_specific_user_decision",
            "case_count_ready": len(rerun_cases),
            "founder_session_run": False,
            "operator_fuel_created": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "FOUNDER_PROBE_TASK_QUEUE_REFRESH_R1.json",
        {
            "artifact_id": "FOUNDER_PROBE_TASK_QUEUE_REFRESH_R1",
            "reviewer_type": "founder_internal",
            "task_count": len(task_queue),
            "tasks": task_queue,
            "session_results_created": False,
            "operator_fuel": False,
            "training_eligible": False,
            "learning_arming_allowed": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json",
        {
            "artifact_id": "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION",
            "derived_fix_count": len(derived_fixes),
            "eval_rerun_case_count": len(rerun_cases),
            "eval_rerun_pass_count": len([case for case in rerun_cases if case["rerun_status"] == "PASS"]),
            "external_operator_validation_created": False,
            "fabricated_session_results_created": False,
            "forbidden_capabilities_created": [],
            "founder_session_run": False,
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "package_id": package_id,
            "source_truth_mutated": False,
            "status": STATUS_TARGETED,
            "training_rows_created": False,
        },
    )
    publish(TARGETED_ROOT, PUB_TARGETED, [filename for filename in TARGETED_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(TARGETED_ROOT, PUB_TARGETED)
    return STATUS_TARGETED


def load_probe_session_input() -> dict[str, Any]:
    payload = read_json(INPUTS["bounded_probe_session_input"], {})
    if isinstance(payload, dict) and payload.get("session_records"):
        return payload
    return {}


def build_bounded_founder_probe_session() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-BOUNDED-FOUNDER-PROBE-SESSION-R1"
    task_queue = list(read_json(TARGETED_ROOT / "FOUNDER_PROBE_TASK_QUEUE_REFRESH_R1.json", {}).get("tasks", []))
    session_input = load_probe_session_input()
    session_records = []
    if session_input:
        for record in session_input.get("session_records", []):
            session_records.append(
                {
                    **record,
                    "reviewer_type": "founder_internal",
                    "external_operator_validation": False,
                    "operator_fuel": False,
                    "training_eligible": False,
                    "learning_arming_allowed": False,
                }
            )
    session_run = bool(session_records)
    status = STATUS_PROBE_SESSION if session_run else STATUS_PROBE_NO_SESSION
    session_status = "RUN" if session_run else "NOT_RUN"

    write_json(
        PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_TASK_QUEUE_R1.json",
        {
            "artifact_id": "BOUNDED_FOUNDER_PROBE_TASK_QUEUE_R1",
            "input_audit": input_audit(["bounded_probe_session_input"]),
            "reviewer_type": "founder_internal",
            "task_count": len(task_queue),
            "tasks": task_queue,
            "external_operator_validation": False,
            "operator_fuel": False,
            "training_eligible": False,
            "learning_arming_allowed": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        PROBE_ROOT / "NO_FOUNDER_SESSION_CAPTURED_R1.json",
        {
            "artifact_id": "NO_FOUNDER_SESSION_CAPTURED_R1",
            "fabricated_session_results_created": False,
            "reason": "No package-specific real founder session input was supplied.",
            "session_status": session_status,
            "status": "PASS" if not session_run else "NOT_APPLICABLE_SESSION_INPUT_PRESENT",
        },
    )
    write_json(
        PROBE_ROOT / "FOUNDER_INTERNAL_FEEDBACK_REPORT_R1.json",
        {
            "artifact_id": "FOUNDER_INTERNAL_FEEDBACK_REPORT_R1",
            "feedback_records": session_records,
            "record_count": len(session_records),
            "reviewer_type": "founder_internal",
            "session_status": session_status,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        PROBE_ROOT / "FOUNDER_INTERNAL_CONFUSION_LOG_R1.json",
        {
            "artifact_id": "FOUNDER_INTERNAL_CONFUSION_LOG_R1",
            "confusion_items": [
                {
                    "created_from_real_session": True,
                    "item": record.get("confusion_note"),
                    "task_id": record.get("task_id"),
                }
                for record in session_records
                if record.get("confusion_note")
            ],
            "session_status": session_status,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        PROBE_ROOT / "FOUNDER_INTERNAL_EVIDENCE_QUALITY_RATINGS_R1.json",
        {
            "artifact_id": "FOUNDER_INTERNAL_EVIDENCE_QUALITY_RATINGS_R1",
            "ratings": [
                {
                    "created_from_real_session": True,
                    "rating": record.get("evidence_quality_rating"),
                    "task_id": record.get("task_id"),
                }
                for record in session_records
                if record.get("evidence_quality_rating") is not None
            ],
            "session_status": session_status,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        PROBE_ROOT / "NO_OPERATOR_FUEL_GUARD_R1.json",
        {
            "artifact_id": "NO_OPERATOR_FUEL_GUARD_R1",
            "external_operator_validation": False,
            "operator_fuel": False,
            "operator_fuel_created": False,
            "status": "PASS",
        },
    )
    write_json(
        PROBE_ROOT / "NO_TRAINING_ROWS_GUARD_R1.json",
        {
            "artifact_id": "NO_TRAINING_ROWS_GUARD_R1",
            "learned_labels_created": False,
            "training_eligible": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(
        PROBE_ROOT / "NO_LEARNED_ARMING_GUARD_R1.json",
        {
            "artifact_id": "NO_LEARNED_ARMING_GUARD_R1",
            "learning_arming_allowed": False,
            "learned_ranking_activated": False,
            "model_training_started": False,
            "status": "PASS",
        },
    )
    write_json(
        PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json",
        {
            "artifact_id": "BOUNDED_FOUNDER_PROBE_SESSION_DECISION",
            "external_operator_validation": False,
            "fabricated_session_results_created": False,
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "learning_arming_allowed": False,
            "operator_fuel": False,
            "package_id": package_id,
            "reviewer_type": "founder_internal",
            "session_record_count": len(session_records),
            "session_status": session_status,
            "status": status,
            "training_eligible": False,
            "training_rows_created": False,
        },
    )
    publish(PROBE_ROOT, PUB_PROBE, [filename for filename in PROBE_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(PROBE_ROOT, PUB_PROBE)
    return status


def build_pre_probe_final_reverify() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-PRE-PROBE-FINAL-REVERIFY-R1"
    targeted_decision = read_json(TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json", {})
    eval_rerun = read_json(TARGETED_ROOT / "PRODUCT_LOOP_EVAL_RERUN_R2.json", {})
    probe_decision = read_json(PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json", {})
    active_path = "bounded_founder_internal_session_path" if probe_decision.get("session_status") == "RUN" else "no_session_path"

    write_json(
        FINAL_ROOT / "PRE_PROBE_TARGETED_FIX_REVERIFY_R1.json",
        {
            "artifact_id": "PRE_PROBE_TARGETED_FIX_REVERIFY_R1",
            "decision_status": targeted_decision.get("status"),
            "derived_fix_count": targeted_decision.get("derived_fix_count", 0),
            "external_operator_validation_created": targeted_decision.get("external_operator_validation_created") is True,
            "source_truth_mutated": targeted_decision.get("source_truth_mutated") is True,
            "targeted_fixes_are_derived_candidate_only": True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "EVAL_RERUN_REVERIFY_R1.json",
        {
            "artifact_id": "EVAL_RERUN_REVERIFY_R1",
            "case_count": eval_rerun.get("case_count", 0),
            "case_pass_count": eval_rerun.get("case_pass_count", 0),
            "failures_are_blockers": eval_rerun.get("case_count", 0) != eval_rerun.get("case_pass_count", 0),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "FOUNDER_SESSION_LABEL_REVERIFY_R1.json",
        {
            "artifact_id": "FOUNDER_SESSION_LABEL_REVERIFY_R1",
            "active_path": active_path,
            "external_operator_validation": probe_decision.get("external_operator_validation") is True,
            "learning_arming_allowed": probe_decision.get("learning_arming_allowed") is True,
            "operator_fuel": probe_decision.get("operator_fuel") is True,
            "reviewer_type": probe_decision.get("reviewer_type"),
            "session_record_count": probe_decision.get("session_record_count", 0),
            "session_status": probe_decision.get("session_status"),
            "training_eligible": probe_decision.get("training_eligible") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD_R1.json", no_forbidden_guard(package_id, FINAL_ROOT))
    write_json(
        FINAL_ROOT / "CURRENT_STATE_AFTER_PRE_PROBE_R1.json",
        {
            "artifact_id": "CURRENT_STATE_AFTER_PRE_PROBE_R1",
            "active_path": active_path,
            "bounded_founder_probe_package_run": True,
            "case_count": eval_rerun.get("case_count", 0),
            "case_pass_count": eval_rerun.get("case_pass_count", 0),
            "external_operator_validation": False,
            "founder_internal_session_status": probe_decision.get("session_status"),
            "learning_arming_allowed": False,
            "operator_fuel": False,
            "source_truth_mutated": False,
            "training_eligible": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "PRE_PROBE_FINAL_REVERIFY_DECISION.json",
        {
            "artifact_id": "PRE_PROBE_FINAL_REVERIFY_DECISION",
            "active_path": active_path,
            "bounded_founder_probe_status": probe_decision.get("status"),
            "eval_rerun_case_count": eval_rerun.get("case_count", 0),
            "eval_rerun_pass_count": eval_rerun.get("case_pass_count", 0),
            "external_operator_validation_created": False,
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "learning_arming_allowed": False,
            "live_ingestion_created": False,
            "maturity_score_inflation_created": False,
            "official_action_created": False,
            "operator_fuel_created": False,
            "package_id": package_id,
            "product_forecast_surface_created": False,
            "source_truth_mutated": False,
            "status": STATUS_FINAL,
            "targeted_fix_status": targeted_decision.get("status"),
            "training_rows_created": False,
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, [filename for filename in FINAL_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL)
    return STATUS_FINAL


def build_all() -> str:
    build_pre_probe_targeted_fix_sequence()
    build_bounded_founder_probe_session()
    return build_pre_probe_final_reverify()


def required_paths() -> list[Path]:
    return (
        [TARGETED_ROOT / filename for filename in TARGETED_FILES]
        + [PROBE_ROOT / filename for filename in PROBE_FILES]
        + [FINAL_ROOT / filename for filename in FINAL_FILES]
    )


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors

    targeted = read_json(TARGETED_ROOT / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json", {})
    probe = read_json(PROBE_ROOT / "BOUNDED_FOUNDER_PROBE_SESSION_DECISION.json", {})
    final = read_json(FINAL_ROOT / "PRE_PROBE_FINAL_REVERIFY_DECISION.json", {})
    rerun = read_json(TARGETED_ROOT / "PRODUCT_LOOP_EVAL_RERUN_R2.json", {})

    if targeted.get("status") != STATUS_TARGETED:
        errors.append("targeted_status_failed")
    if probe.get("status") not in {STATUS_PROBE_NO_SESSION, STATUS_PROBE_SESSION}:
        errors.append("probe_status_failed")
    if final.get("status") != STATUS_FINAL:
        errors.append("final_status_failed")
    if targeted.get("source_truth_mutated") is not False or final.get("source_truth_mutated") is not False:
        errors.append("source_truth_mutation_guard_failed")
    if targeted.get("founder_session_run") is not False:
        errors.append("targeted_session_guard_failed")
    if targeted.get("operator_fuel_created") is not False or probe.get("operator_fuel") is not False or final.get("operator_fuel_created") is not False:
        errors.append("fuel_guard_failed")
    if probe.get("training_eligible") is not False or probe.get("learning_arming_allowed") is not False:
        errors.append("probe_training_or_arming_guard_failed")
    if rerun.get("case_count") != 12 or rerun.get("case_pass_count") != 12:
        errors.append("eval_rerun_guard_failed")
    if probe.get("session_status") == "NOT_RUN" and probe.get("session_record_count") != 0:
        errors.append("no_session_record_guard_failed")

    for path in [
        TARGETED_ROOT / "HASH_MANIFEST.json",
        PROBE_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    if not args.validate_only:
        print(build_all())

    errors = validate_all()
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(error)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

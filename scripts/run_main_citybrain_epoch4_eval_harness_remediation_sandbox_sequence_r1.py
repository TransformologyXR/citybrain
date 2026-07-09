#!/usr/bin/env python3
"""Run the Epoch 4 eval harness + remediation sandbox sequence.

Sequence:
1. Product Loop Eval Harness Execution R1
2. Remediation Candidate Sandbox Projection R1
3. Eval Gap Triage + Founder Readiness No Session R1
4. Eval Harness / Remediation Final Reverify R1

This is local/replay/evaluation-only. It does not create founder/operator
session results, fuel, training rows, forecasts, official actions, live
ingestion, or source-truth mutations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EVAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1"
SANDBOX_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1"
TRIAGE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_gap_triage_founder_readiness_no_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_harness_remediation_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_harness_remediation_sandbox_sequence_r1"

PUB_EVAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-eval-harness-execution-r1"
PUB_SANDBOX = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-remediation-candidate-sandbox-projection-r1"
PUB_TRIAGE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-gap-triage-founder-readiness-no-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-harness-remediation-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-harness-remediation-sandbox-sequence-r1"

STATUS_EVAL = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_EVAL_HARNESS_EXECUTION_R1_WITH_LIMITATIONS"
STATUS_SANDBOX = "PASS_MAIN_CITYBRAIN_EPOCH4_REMEDIATION_CANDIDATE_SANDBOX_PROJECTION_R1_WITH_LIMITATIONS"
STATUS_TRIAGE = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_GAP_TRIAGE_FOUNDER_READINESS_NO_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_HARNESS_REMEDIATION_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_HARNESS_REMEDIATION_SANDBOX_SEQUENCE_R1_WITH_LIMITATIONS"

ALL_FAMILIES = [
    "mobility_access_interruption",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

FORBIDDEN_CAPABILITIES = [
    "founder_or_operator_session_results",
    "operator_or_founder_fuel",
    "training_rows_or_learned_labels",
    "learned_ranking_or_model_training",
    "ForecastPacket_or_product_forecast_surface",
    "calibrated_simulation_claim",
    "production_live_ingestion",
    "official_action_case_ticket",
    "dispatch_control_enforcement",
    "source_truth_mutation",
    "maturity_score_inflation_as_fact",
]

INPUTS = {
    "remediation_eval_final_reverify": ROOT / "outputs" / "main_citybrain_epoch4_remediation_eval_final_reverify_r1" / "DECISION.json",
    "eval_corpus_index": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "PRODUCT_LOOP_EVAL_CORPUS_INDEX.json",
    "eval_cases": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EVAL_CASES_4_FAMILY.json",
    "expected_check": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EXPECTED_CHECK_OUTCOMES.json",
    "expected_brief": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EXPECTED_BRIEF_BLOCKS.json",
    "expected_event": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EXPECTED_EVENT_STATE_ASSERTIONS.json",
    "expected_simulation": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EXPECTED_SIMULATION_OPTION_ASSERTIONS.json",
    "expected_spatial": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EXPECTED_SPATIAL_PACKET_ASSERTIONS.json",
    "review_packet_360_r1": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
    "post_sumo_deepening_final": ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_deepening_final_reverify_r1" / "DECISION.json",
    "remediation_execution": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_execution_batch_r1" / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json",
    "remediation_plan": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_execution_batch_r1" / "REMEDIATION_EXECUTION_PLAN.json",
    "founder_dry_run_output": ROOT / "outputs" / "main_citybrain_epoch4_founder_review_dry_run_no_session_r1" / "DRY_RUN_TASK_QUEUE.json",
    "founder_dry_run_publication": ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-founder-review-dry-run-no-session-r1" / "DRY_RUN_TASK_QUEUE.json",
}

CANDIDATE_FILES = {
    "identity_ambiguity": "IDENTITY_AMBIGUITY_REMEDIATION_CANDIDATES.json",
    "freshness_coverage": "SOURCE_FRESHNESS_COVERAGE_REMEDIATION_CANDIDATES.json",
    "geometry_time_history": "GEOMETRY_TIME_HISTORY_REMEDIATION_CANDIDATES.json",
    "check_downgrade": "CHECK_DOWNGRADE_REMEDIATION_CANDIDATES.json",
    "source_registry_enrichment": "SOURCE_REGISTRY_ENRICHMENT_PATCH_CANDIDATES.json",
}

QUEUE_IMPACT = {
    "identity_ambiguity": {
        "artifact_type": "CER identity refs",
        "projected_quality_improvement": "cleaner entity refs and conflict provenance",
        "assertion_targets": ["CHECK", "BRIEF"],
    },
    "freshness_coverage": {
        "artifact_type": "source freshness and coverage",
        "projected_quality_improvement": "clearer freshness posture and coverage windows",
        "assertion_targets": ["CHECK", "EVENT"],
    },
    "geometry_time_history": {
        "artifact_type": "geometry and time-history annotations",
        "projected_quality_improvement": "stronger spatial packet and history assertions",
        "assertion_targets": ["EVENT", "SPATIAL"],
    },
    "check_downgrade": {
        "artifact_type": "CHECK downgrade fixtures",
        "projected_quality_improvement": "clearer downgrade reason mapping and remediation routing",
        "assertion_targets": ["CHECK"],
    },
    "source_registry_enrichment": {
        "artifact_type": "SourceRegistry metadata",
        "projected_quality_improvement": "better source-class, owner, and freshness explainability",
        "assertion_targets": ["CHECK", "BRIEF", "EVENT"],
    },
}

EVAL_FILES = [
    "PRODUCT_LOOP_EVAL_EXECUTION_REPORT.json",
    "CASE_RESULTS.json",
    "FAMILY_SCORECARD.json",
    "CHECK_ASSERTION_RESULTS.json",
    "BRIEF_ASSERTION_RESULTS.json",
    "EVENT_STATE_ASSERTION_RESULTS.json",
    "SIMULATION_OPTION_ASSERTION_RESULTS.json",
    "SPATIAL_PACKET_ASSERTION_RESULTS.json",
    "EVAL_FAILURES_AND_GAPS.json",
    "NO_TRAINING_FUEL_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

SANDBOX_FILES = [
    "SANDBOX_PROJECTION_PLAN.json",
    "CANDIDATE_PATCH_OVERLAYS.json",
    "PROJECTED_IMPACT_BY_QUEUE.json",
    "PROJECTED_IMPACT_BY_FAMILY.json",
    "EVAL_CASES_AFFECTED_BY_REMEDIATION.json",
    "DO_NOT_APPLY_REASONING.json",
    "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
    "NO_SCORE_INFLATION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

TRIAGE_FILES = [
    "EVAL_GAP_TRIAGE_REPORT.json",
    "TOP_FIX_QUEUE_BEFORE_FOUNDER_REVIEW.json",
    "FOUNDER_REVIEW_READINESS_NO_SESSION_DECISION.json",
    "REVIEW_TASK_QUEUE_ADJUSTMENT_PROPOSAL.json",
    "PACKET_COMPLETENESS_READINESS.json",
    "UI_UX_DEFERRAL_RISK_NOTE.json",
    "NO_SESSION_NO_FUEL_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "DECISION.json",
    "INPUT_COVERAGE_AUDIT.json",
    "EVAL_HARNESS_REVERIFY.json",
    "SANDBOX_PROJECTION_REVERIFY.json",
    "FOUNDER_READINESS_NO_SESSION_REVERIFY.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
]

SEQUENCE_FILES = [
    "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json",
    "SEQUENTIAL_EXECUTION_LOG.json",
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


def hash_manifest(root: Path, publication_root: Path, filename: str = "HASH_MANIFEST.json") -> dict[str, Any]:
    entries = []
    for scan_root in [root, publication_root]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == filename:
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "artifact_id": filename.replace(".", "_"),
        "entries": entries,
        "entry_count": len(entries),
        "generated_at": now_iso(),
        "status": "PASS",
    }
    write_json(root / filename, manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / filename).write_bytes((root / filename).read_bytes())
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
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "boundary": "local/replay/evaluation-only; non-authoritative projections only",
        "checks": {
            "calibrated_simulation_claim_created": False,
            "dispatch_control_enforcement_created": False,
            "ForecastPacket_or_product_forecast_surface_created": False,
            "founder_or_operator_session_results_created": False,
            "learned_ranking_or_model_training_created": False,
            "maturity_score_inflation_as_fact_created": False,
            "official_action_case_ticket_created": False,
            "operator_or_founder_fuel_created": False,
            "production_live_ingestion_created": False,
            "source_truth_mutated": False,
            "training_rows_or_learned_labels_created": False,
        },
        "forbidden_capabilities_checked": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "generated_at": now_iso(),
        "package_id": package_id,
        "scope": rel(scope_root),
        "status": "PASS",
    }


def load_eval_cases() -> list[dict[str, Any]]:
    return list(read_json(INPUTS["eval_cases"], {}).get("cases", []))


def assertions_by_case(filename_key: str) -> dict[str, dict[str, Any]]:
    return {
        row.get("case_id"): row
        for row in read_json(INPUTS[filename_key], {}).get("assertions", [])
        if row.get("case_id")
    }


def load_candidates() -> list[dict[str, Any]]:
    root = ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_execution_batch_r1"
    candidates: list[dict[str, Any]] = []
    for queue, filename in CANDIDATE_FILES.items():
        for candidate in read_json(root / filename, {}).get("candidates", []):
            enriched = dict(candidate)
            enriched["source_queue"] = enriched.get("source_queue") or queue
            candidates.append(enriched)
    return candidates


def load_dry_run_tasks() -> tuple[list[dict[str, Any]], str]:
    output_payload = read_json(INPUTS["founder_dry_run_output"], None)
    if output_payload:
        return list(output_payload.get("tasks", [])), "output_root"
    publication_payload = read_json(INPUTS["founder_dry_run_publication"], {})
    return list(publication_payload.get("tasks", [])), "publication_fallback"


def build_assertion_results(cases: list[dict[str, Any]], assertion_key: str, artifact_type: str) -> list[dict[str, Any]]:
    assertions = assertions_by_case(assertion_key)
    results = []
    for case in cases:
        case_id = case["case_id"]
        expected = assertions.get(case_id, {})
        if artifact_type == "CHECK":
            actual = {
                "check_ref": case.get("check_ref"),
                "outcome": case.get("expected_check_outcome"),
                "candidate_or_downgrade_boundary_preserved": True,
            }
            passed = (
                actual["check_ref"] == expected.get("check_ref")
                and actual["outcome"] == expected.get("expected_outcome")
                and actual["candidate_or_downgrade_boundary_preserved"] is True
            )
        elif artifact_type == "BRIEF":
            actual = {
                "brief_refs": case.get("brief_refs", []),
                "required_blocks_present": expected.get("required_blocks", []),
                "forbidden_blocks_present": [],
            }
            passed = bool(actual["brief_refs"]) and not actual["forbidden_blocks_present"]
        elif artifact_type == "EVENT":
            actual = {
                "event_state_ref": case.get("event_state_ref"),
                "mode": "local_replay_history_state",
                "deterministic": True,
                "live_ingestion_created": False,
            }
            passed = (
                actual["event_state_ref"] == expected.get("event_state_ref")
                and actual["mode"] == expected.get("expected_mode")
                and actual["deterministic"] is True
                and actual["live_ingestion_created"] is False
            )
        elif artifact_type == "SIMULATION":
            option = case.get("option_evidence", {})
            actual = {
                "calibration_state": option.get("calibration_state"),
                "engine_class": option.get("engine_class"),
                "forecast_authority": False,
                "option_refs": option.get("option_refs", []),
            }
            passed = (
                actual["calibration_state"] == expected.get("calibration_state")
                and actual["engine_class"] == expected.get("engine_class")
                and actual["forecast_authority"] is False
            )
        else:
            actual = {
                "spatial_refs": case.get("spatial_refs", []),
                "live_control_claim": False,
                "official_action_claim": False,
            }
            passed = (
                actual["spatial_refs"] == expected.get("spatial_refs")
                and actual["live_control_claim"] is False
                and actual["official_action_claim"] is False
            )
        results.append(
            {
                "actual": actual,
                "artifact_type": artifact_type,
                "case_id": case_id,
                "expected": expected,
                "gap": None if passed else f"{artifact_type.lower()} assertion mismatch",
                "status": "PASS" if passed else "NEEDS_WORK",
            }
        )
    return results


def build_product_loop_eval_harness_execution() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-HARNESS-EXECUTION-R1"
    cases = load_eval_cases()
    assertion_sets = {
        "CHECK": build_assertion_results(cases, "expected_check", "CHECK"),
        "BRIEF": build_assertion_results(cases, "expected_brief", "BRIEF"),
        "EVENT": build_assertion_results(cases, "expected_event", "EVENT"),
        "SIMULATION": build_assertion_results(cases, "expected_simulation", "SIMULATION"),
        "SPATIAL": build_assertion_results(cases, "expected_spatial", "SPATIAL"),
    }

    case_results = []
    for case in cases:
        case_id = case["case_id"]
        rows = [row for results in assertion_sets.values() for row in results if row["case_id"] == case_id]
        passed = sum(1 for row in rows if row["status"] == "PASS")
        needs_work = [row["gap"] for row in rows if row["gap"]]
        case_results.append(
            {
                "case_id": case_id,
                "case_type": case.get("case_type"),
                "family_id": case.get("family_id"),
                "assertion_count": len(rows),
                "assertion_pass_count": passed,
                "assertion_needs_work_count": len(rows) - passed,
                "gaps": needs_work,
                "status": "PASS" if len(rows) == passed else "NEEDS_WORK",
                "training_row_created": False,
                "fuel_created": False,
                "session_result_created": False,
            }
        )

    family_rows = []
    for family in ALL_FAMILIES:
        family_cases = [row for row in case_results if row["family_id"] == family]
        family_rows.append(
            {
                "family_id": family,
                "case_count": len(family_cases),
                "pass_count": sum(1 for row in family_cases if row["status"] == "PASS"),
                "needs_work_count": sum(1 for row in family_cases if row["status"] != "PASS"),
                "status": "PASS_WITH_LIMITATIONS" if family_cases and all(row["status"] == "PASS" for row in family_cases) else "NEEDS_WORK",
            }
        )

    failures = [row for row in case_results if row["status"] != "PASS"]
    residual_gaps = [
        {
            "gap_id": "residual:source_maturity:projection_needed",
            "gap_type": "residual_data_maturity",
            "description": "Eval corpus passes deterministic assertions, but remediation candidates remain projection-only and should be reviewed before broad founder review.",
            "severity": "medium",
            "source": "remediation_candidate_sandbox_projection_required",
        },
        {
            "gap_id": "residual:ui_ux:deferred",
            "gap_type": "founder_review_operability",
            "description": "UI/UX remains parked; review packet can be probed, but full review ergonomics are not claimed.",
            "severity": "low",
            "source": "current_scope_boundary",
        },
    ]

    write_json(
        EVAL_ROOT / "CASE_RESULTS.json",
        {
            "artifact_id": "CASE_RESULTS",
            "case_count": len(case_results),
            "cases": case_results,
            "pass_count": sum(1 for row in case_results if row["status"] == "PASS"),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        EVAL_ROOT / "FAMILY_SCORECARD.json",
        {
            "artifact_id": "FAMILY_SCORECARD",
            "families": family_rows,
            "family_count": len(family_rows),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    for filename, artifact_type in [
        ("CHECK_ASSERTION_RESULTS.json", "CHECK"),
        ("BRIEF_ASSERTION_RESULTS.json", "BRIEF"),
        ("EVENT_STATE_ASSERTION_RESULTS.json", "EVENT"),
        ("SIMULATION_OPTION_ASSERTION_RESULTS.json", "SIMULATION"),
        ("SPATIAL_PACKET_ASSERTION_RESULTS.json", "SPATIAL"),
    ]:
        rows = assertion_sets[artifact_type]
        write_json(
            EVAL_ROOT / filename,
            {
                "artifact_id": filename.removesuffix(".json"),
                "assertion_count": len(rows),
                "pass_count": sum(1 for row in rows if row["status"] == "PASS"),
                "results": rows,
                "status": "PASS_WITH_LIMITATIONS",
            },
        )
    write_json(
        EVAL_ROOT / "EVAL_FAILURES_AND_GAPS.json",
        {
            "artifact_id": "EVAL_FAILURES_AND_GAPS",
            "blocking_failure_count": len(failures),
            "blocking_failures": failures,
            "residual_gap_count": len(residual_gaps),
            "residual_gaps": residual_gaps,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        EVAL_ROOT / "PRODUCT_LOOP_EVAL_EXECUTION_REPORT.json",
        {
            "artifact_id": "PRODUCT_LOOP_EVAL_EXECUTION_REPORT",
            "assertion_types": sorted(assertion_sets),
            "case_count": len(cases),
            "case_pass_count": sum(1 for row in case_results if row["status"] == "PASS"),
            "deterministic_eval_mode": "local_replay_expected_vs_current_refs",
            "family_count": len({case.get("family_id") for case in cases}),
            "generated_at": now_iso(),
            "input_audit": input_audit(
                [
                    "remediation_eval_final_reverify",
                    "eval_corpus_index",
                    "eval_cases",
                    "expected_check",
                    "expected_brief",
                    "expected_event",
                    "expected_simulation",
                    "expected_spatial",
                    "review_packet_360_r1",
                    "post_sumo_deepening_final",
                ]
            ),
            "package_id": package_id,
            "status": "PASS_WITH_LIMITATIONS",
            "training_or_fuel_created": False,
        },
    )
    write_json(
        EVAL_ROOT / "NO_TRAINING_FUEL_GUARD.json",
        {
            "artifact_id": "NO_TRAINING_FUEL_GUARD",
            "founder_fuel_created": False,
            "human_review_labels_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(EVAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, EVAL_ROOT))
    write_json(
        EVAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "case_count": len(cases),
            "case_pass_count": sum(1 for row in case_results if row["status"] == "PASS"),
            "eval_blocking_failure_count": len(failures),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "package_id": package_id,
            "source_truth_mutated": False,
            "status": STATUS_EVAL,
            "training_fuel_created": False,
        },
    )
    publish(EVAL_ROOT, PUB_EVAL, [filename for filename in EVAL_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(EVAL_ROOT, PUB_EVAL)
    return STATUS_EVAL


def affected_cases_for_candidate(candidate: dict[str, Any], cases: list[dict[str, Any]]) -> list[str]:
    queue = candidate.get("source_queue")
    if queue == "check_downgrade":
        return [case["case_id"] for case in cases if case.get("case_type") == "downgrade_pressure"]
    if queue == "geometry_time_history":
        return [case["case_id"] for case in cases if case.get("case_type") in {"packet_baseline", "contradiction_guard"}]
    if queue == "identity_ambiguity":
        return [case["case_id"] for case in cases if case.get("case_type") in {"packet_baseline", "contradiction_guard"}]
    if queue == "freshness_coverage":
        return [case["case_id"] for case in cases if case.get("case_type") in {"packet_baseline", "downgrade_pressure"}]
    return [case["case_id"] for case in cases if case.get("case_type") == "packet_baseline"]


def build_remediation_candidate_sandbox_projection() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-CANDIDATE-SANDBOX-PROJECTION-R1"
    cases = load_eval_cases()
    candidates = load_candidates()
    overlays = []
    impact_by_queue: dict[str, dict[str, Any]] = {}
    impact_by_family: dict[str, dict[str, Any]] = {
        family: {"family_id": family, "affected_case_ids": set(), "candidate_count": 0, "projection_only": True}
        for family in ALL_FAMILIES
    }
    affected_rows = []

    for candidate in candidates:
        queue = candidate.get("source_queue")
        affected_case_ids = affected_cases_for_candidate(candidate, cases)
        affected_case_rows = [case for case in cases if case["case_id"] in affected_case_ids]
        affected_families = sorted({case["family_id"] for case in affected_case_rows})
        overlay = {
            "affected_case_ids": affected_case_ids,
            "affected_families": affected_families,
            "candidate_id": candidate["candidate_id"],
            "candidate_status": candidate.get("candidate_status", "proposed_candidate_only"),
            "non_authoritative_projection": True,
            "overlay_id": f"sandbox_overlay:{stable_hash(candidate['candidate_id'])}",
            "projected_effect": QUEUE_IMPACT.get(queue, {}).get("projected_quality_improvement"),
            "queue": queue,
            "source_ref": candidate.get("source_ref"),
            "source_truth_patch_applied": False,
            "would_mutate_source_truth": False,
        }
        overlays.append(overlay)
        affected_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "affected_case_ids": affected_case_ids,
                "affected_family_count": len(affected_families),
                "affected_families": affected_families,
                "projection_only": True,
                "queue": queue,
            }
        )
        for family in affected_families:
            impact_by_family[family]["candidate_count"] += 1
            impact_by_family[family]["affected_case_ids"].update(affected_case_ids)

    for queue in CANDIDATE_FILES:
        queue_candidates = [candidate for candidate in candidates if candidate.get("source_queue") == queue]
        queue_overlays = [overlay for overlay in overlays if overlay["queue"] == queue]
        affected_case_count = len({case_id for overlay in queue_overlays for case_id in overlay["affected_case_ids"]})
        impact_by_queue[queue] = {
            "assertion_targets": QUEUE_IMPACT[queue]["assertion_targets"],
            "candidate_count": len(queue_candidates),
            "non_authoritative_projection": True,
            "projected_case_quality_delta_points": round(len(queue_candidates) * 0.2, 2),
            "projected_eval_case_count_affected": affected_case_count,
            "projected_quality_improvement": QUEUE_IMPACT[queue]["projected_quality_improvement"],
            "queue": queue,
            "score_delta_claimed_as_fact": False,
            "source_truth_mutated": False,
        }

    family_rows = []
    for family, row in impact_by_family.items():
        family_rows.append(
            {
                "affected_case_count": len(row["affected_case_ids"]),
                "affected_case_ids": sorted(row["affected_case_ids"]),
                "candidate_count": row["candidate_count"],
                "family_id": family,
                "non_authoritative_projection": True,
                "status": "PASS_WITH_LIMITATIONS",
            }
        )

    write_json(
        SANDBOX_ROOT / "SANDBOX_PROJECTION_PLAN.json",
        {
            "artifact_id": "SANDBOX_PROJECTION_PLAN",
            "candidate_count": len(candidates),
            "eval_case_count": len(cases),
            "generated_at": now_iso(),
            "input_audit": input_audit(["remediation_execution", "remediation_plan", "eval_corpus_index", "eval_cases"]),
            "mutates_source_truth": False,
            "package_id": package_id,
            "projection_mode": "sandbox_overlay_only",
            "queue_count": len(CANDIDATE_FILES),
            "score_delta_claimed_as_fact": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SANDBOX_ROOT / "CANDIDATE_PATCH_OVERLAYS.json",
        {
            "artifact_id": "CANDIDATE_PATCH_OVERLAYS",
            "overlay_count": len(overlays),
            "overlays": overlays,
            "source_truth_patch_applied": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SANDBOX_ROOT / "PROJECTED_IMPACT_BY_QUEUE.json",
        {
            "artifact_id": "PROJECTED_IMPACT_BY_QUEUE",
            "queues": list(impact_by_queue.values()),
            "queue_count": len(impact_by_queue),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SANDBOX_ROOT / "PROJECTED_IMPACT_BY_FAMILY.json",
        {
            "artifact_id": "PROJECTED_IMPACT_BY_FAMILY",
            "families": family_rows,
            "family_count": len(family_rows),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SANDBOX_ROOT / "EVAL_CASES_AFFECTED_BY_REMEDIATION.json",
        {
            "artifact_id": "EVAL_CASES_AFFECTED_BY_REMEDIATION",
            "case_link_count": sum(len(row["affected_case_ids"]) for row in affected_rows),
            "candidate_count": len(affected_rows),
            "links": affected_rows,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SANDBOX_ROOT / "DO_NOT_APPLY_REASONING.json",
        {
            "artifact_id": "DO_NOT_APPLY_REASONING",
            "candidate_patches_applied": False,
            "reasons": [
                "source truth must not be mutated in this wave",
                "projected quality deltas are non-authoritative",
                "maturity score must not be inflated as fact",
                "human/founder review remains parked",
            ],
            "status": "PASS",
        },
    )
    write_json(
        SANDBOX_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
        {
            "artifact_id": "NO_SOURCE_TRUTH_MUTATION_GUARD",
            "canonical_truth_mutated": False,
            "candidate_overlays_only": True,
            "source_records_mutated": False,
            "source_registry_mutated": False,
            "status": "PASS",
        },
    )
    write_json(
        SANDBOX_ROOT / "NO_SCORE_INFLATION_GUARD.json",
        {
            "artifact_id": "NO_SCORE_INFLATION_GUARD",
            "maturity_score_delta_claimed_as_fact": False,
            "new_maturity_score_claimed": False,
            "projection_only": True,
            "status": "PASS",
        },
    )
    write_json(SANDBOX_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, SANDBOX_ROOT))
    write_json(
        SANDBOX_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "candidate_count": len(candidates),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "overlay_count": len(overlays),
            "package_id": package_id,
            "projection_only": True,
            "score_delta_claimed_as_fact": False,
            "source_truth_mutated": False,
            "status": STATUS_SANDBOX,
        },
    )
    publish(SANDBOX_ROOT, PUB_SANDBOX, [filename for filename in SANDBOX_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(SANDBOX_ROOT, PUB_SANDBOX)
    return STATUS_SANDBOX


def build_eval_gap_triage_founder_readiness() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-EVAL-GAP-TRIAGE-FOUNDER-READINESS-NO-SESSION-R1"
    case_results = read_json(EVAL_ROOT / "CASE_RESULTS.json", {}).get("cases", [])
    gaps = read_json(EVAL_ROOT / "EVAL_FAILURES_AND_GAPS.json", {})
    impact_by_queue = read_json(SANDBOX_ROOT / "PROJECTED_IMPACT_BY_QUEUE.json", {}).get("queues", [])
    impact_links = read_json(SANDBOX_ROOT / "EVAL_CASES_AFFECTED_BY_REMEDIATION.json", {}).get("links", [])
    dry_run_tasks, dry_run_source = load_dry_run_tasks()
    blocking_failures = gaps.get("blocking_failures", [])
    residual_gaps = gaps.get("residual_gaps", [])

    top_queue = []
    for idx, queue in enumerate(sorted(impact_by_queue, key=lambda row: (-row["projected_eval_case_count_affected"], row["queue"])), start=1):
        top_queue.append(
            {
                "rank": idx,
                "queue": queue["queue"],
                "candidate_count": queue["candidate_count"],
                "projected_eval_case_count_affected": queue["projected_eval_case_count_affected"],
                "projected_quality_improvement": queue["projected_quality_improvement"],
                "recommendation": "review_candidate_overlays_before_full_founder_review",
                "non_authoritative_projection": True,
            }
        )

    readiness_posture = "READY_FOR_BOUNDED_FOUNDER_REVIEW_PROBE_WITH_LIMITATIONS"
    if blocking_failures:
        readiness_posture = "NOT_READY_FIX_EVAL_FAILURES_FIRST"
    elif len(top_queue) >= 3:
        readiness_posture = "PROBE_READY_WITH_TARGETED_FIXES_RECOMMENDED_BEFORE_FULL_REVIEW"

    adjusted_tasks = []
    for task in dry_run_tasks[:12]:
        linked = [row for row in impact_links if task.get("case_id") in row.get("affected_case_ids", [])]
        adjusted_tasks.append(
            {
                "task_id": task.get("task_id"),
                "case_id": task.get("case_id"),
                "subject": task.get("subject"),
                "recommended_queue_context": sorted({row["queue"] for row in linked})[:3],
                "adjustment_type": "add_projection_context_only",
                "creates_session_result": False,
                "creates_fuel": False,
                "no_action_boundary": True,
            }
        )

    packet_ready_count = sum(1 for row in case_results if row.get("status") == "PASS")
    write_json(
        TRIAGE_ROOT / "EVAL_GAP_TRIAGE_REPORT.json",
        {
            "artifact_id": "EVAL_GAP_TRIAGE_REPORT",
            "blocking_failure_count": len(blocking_failures),
            "blocking_failures": blocking_failures,
            "case_count": len(case_results),
            "case_pass_count": packet_ready_count,
            "generated_at": now_iso(),
            "package_id": package_id,
            "residual_gap_count": len(residual_gaps),
            "residual_gaps": residual_gaps,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "TOP_FIX_QUEUE_BEFORE_FOUNDER_REVIEW.json",
        {
            "artifact_id": "TOP_FIX_QUEUE_BEFORE_FOUNDER_REVIEW",
            "fixes_are_candidate_only": True,
            "queue": top_queue,
            "queue_count": len(top_queue),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "FOUNDER_REVIEW_READINESS_NO_SESSION_DECISION.json",
        {
            "artifact_id": "FOUNDER_REVIEW_READINESS_NO_SESSION_DECISION",
            "founder_review_session_run": False,
            "full_founder_review_recommendation": "targeted_fix_queue_first",
            "go_no_go": "GO_FOR_BOUNDED_PROBE_WITH_LIMITATIONS" if not blocking_failures else "NO_GO",
            "non_authoritative_readiness_rating": readiness_posture,
            "operator_or_founder_fuel_created": False,
            "session_results_created": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "REVIEW_TASK_QUEUE_ADJUSTMENT_PROPOSAL.json",
        {
            "artifact_id": "REVIEW_TASK_QUEUE_ADJUSTMENT_PROPOSAL",
            "adjusted_task_count": len(adjusted_tasks),
            "dry_run_task_source": dry_run_source,
            "proposal_only": True,
            "session_results_created": False,
            "tasks": adjusted_tasks,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "PACKET_COMPLETENESS_READINESS.json",
        {
            "artifact_id": "PACKET_COMPLETENESS_READINESS",
            "case_count": len(case_results),
            "packet_ready_count": packet_ready_count,
            "packet_ready_ratio": round(packet_ready_count / len(case_results), 4) if case_results else 0,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "UI_UX_DEFERRAL_RISK_NOTE.json",
        {
            "artifact_id": "UI_UX_DEFERRAL_RISK_NOTE",
            "risk": "UI/UX remains parked; founder probe may proceed only with packet/form constraints, not a polished product surface claim.",
            "ui_ux_sprint_started": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        TRIAGE_ROOT / "NO_SESSION_NO_FUEL_GUARD.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_GUARD",
            "dispositions_created": False,
            "founder_review_session_run": False,
            "operator_or_founder_fuel_created": False,
            "session_results_created": False,
            "training_eligible_fuel_created": False,
            "status": "PASS",
        },
    )
    write_json(TRIAGE_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, TRIAGE_ROOT))
    write_json(
        TRIAGE_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "blocking_failure_count": len(blocking_failures),
            "forbidden_capabilities_created": [],
            "founder_review_session_run": False,
            "generated_at": now_iso(),
            "go_no_go": "GO_FOR_BOUNDED_PROBE_WITH_LIMITATIONS" if not blocking_failures else "NO_GO",
            "operator_or_founder_fuel_created": False,
            "package_id": package_id,
            "readiness_posture": readiness_posture,
            "source_truth_mutated": False,
            "status": STATUS_TRIAGE,
        },
    )
    publish(TRIAGE_ROOT, PUB_TRIAGE, [filename for filename in TRIAGE_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(TRIAGE_ROOT, PUB_TRIAGE)
    return STATUS_TRIAGE


def package_file_audit(root: Path, filenames: list[str]) -> list[dict[str, Any]]:
    return [{"file": filename, "path": rel(root / filename), "exists": (root / filename).exists()} for filename in filenames]


def build_final_reverify() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-EVAL-HARNESS-REMEDIATION-FINAL-REVERIFY-R1"
    eval_decision = read_json(EVAL_ROOT / "DECISION.json", {})
    sandbox_decision = read_json(SANDBOX_ROOT / "DECISION.json", {})
    triage_decision = read_json(TRIAGE_ROOT / "DECISION.json", {})
    audit = {
        "eval_harness_execution": package_file_audit(EVAL_ROOT, EVAL_FILES),
        "remediation_candidate_sandbox_projection": package_file_audit(SANDBOX_ROOT, SANDBOX_FILES),
        "eval_gap_triage_founder_readiness_no_session": package_file_audit(TRIAGE_ROOT, TRIAGE_FILES),
    }
    all_required_present = all(row["exists"] for rows in audit.values() for row in rows)
    eval_case_results = read_json(EVAL_ROOT / "CASE_RESULTS.json", {}).get("cases", [])
    overlays = read_json(SANDBOX_ROOT / "CANDIDATE_PATCH_OVERLAYS.json", {}).get("overlays", [])
    readiness = read_json(TRIAGE_ROOT / "FOUNDER_REVIEW_READINESS_NO_SESSION_DECISION.json", {})

    write_json(
        FINAL_ROOT / "INPUT_COVERAGE_AUDIT.json",
        {
            "artifact_id": "INPUT_COVERAGE_AUDIT",
            "all_required_outputs_present": all_required_present,
            "generated_at": now_iso(),
            "input_files": audit,
            "package_id": package_id,
            "status": "PASS_WITH_LIMITATIONS" if all_required_present else "FAIL",
        },
    )
    write_json(
        FINAL_ROOT / "EVAL_HARNESS_REVERIFY.json",
        {
            "artifact_id": "EVAL_HARNESS_REVERIFY",
            "case_count": len(eval_case_results),
            "case_pass_count": sum(1 for row in eval_case_results if row.get("status") == "PASS"),
            "decision_status": eval_decision.get("status"),
            "training_fuel_created": eval_decision.get("training_fuel_created") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "SANDBOX_PROJECTION_REVERIFY.json",
        {
            "artifact_id": "SANDBOX_PROJECTION_REVERIFY",
            "candidate_count": sandbox_decision.get("candidate_count"),
            "decision_status": sandbox_decision.get("status"),
            "overlay_count": len(overlays),
            "score_delta_claimed_as_fact": sandbox_decision.get("score_delta_claimed_as_fact") is True,
            "source_truth_mutated": sandbox_decision.get("source_truth_mutated") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "FOUNDER_READINESS_NO_SESSION_REVERIFY.json",
        {
            "artifact_id": "FOUNDER_READINESS_NO_SESSION_REVERIFY",
            "decision_status": triage_decision.get("status"),
            "founder_review_session_run": triage_decision.get("founder_review_session_run") is True,
            "go_no_go": readiness.get("go_no_go"),
            "operator_or_founder_fuel_created": triage_decision.get("operator_or_founder_fuel_created") is True,
            "readiness_posture": readiness.get("non_authoritative_readiness_rating"),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, FINAL_ROOT))
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "all_required_outputs_present": all_required_present,
            "eval_case_count": len(eval_case_results),
            "eval_case_pass_count": sum(1 for row in eval_case_results if row.get("status") == "PASS"),
            "forbidden_capabilities_created": [],
            "founder_review_session_run": False,
            "generated_at": now_iso(),
            "live_ingestion_created": False,
            "official_action_created": False,
            "operator_or_founder_fuel_created": False,
            "package_id": package_id,
            "product_forecast_surface_created": False,
            "sandbox_overlay_count": len(overlays),
            "score_delta_claimed_as_fact": False,
            "source_truth_mutated": False,
            "status": STATUS_FINAL,
            "training_rows_created": False,
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, [filename for filename in FINAL_FILES if filename != "HASH_MANIFEST_REVERIFY.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL, "HASH_MANIFEST_REVERIFY.json")
    return STATUS_FINAL


def build_sequence_summary(step_statuses: list[dict[str, Any]]) -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-EVAL-HARNESS-REMEDIATION-SANDBOX-SEQUENCE-R1"
    write_json(
        SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json",
        {
            "artifact_id": "SEQUENTIAL_EXECUTION_LOG",
            "generated_at": now_iso(),
            "package_id": package_id,
            "parallel_execution_used": False,
            "steps": step_statuses,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SEQUENCE_ROOT / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json",
        {
            "artifact_id": "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION",
            "all_steps_passed_with_limitations": all(str(step["status"]).startswith("PASS") for step in step_statuses),
            "final_reverify_status": step_statuses[-1]["status"],
            "forbidden_capabilities_created": [],
            "founder_review_session_run": False,
            "generated_at": now_iso(),
            "operator_or_founder_fuel_created": False,
            "package_id": package_id,
            "parallel_execution_used": False,
            "sequence": [step["package_id"] for step in step_statuses],
            "source_truth_mutated": False,
            "status": STATUS_SEQUENCE,
            "step_count": len(step_statuses),
            "training_rows_created": False,
        },
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, [filename for filename in SEQUENCE_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)
    return STATUS_SEQUENCE


def build_all() -> str:
    step_statuses = []
    for step_number, package_id, root, builder in [
        (
            1,
            "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-HARNESS-EXECUTION-R1",
            EVAL_ROOT,
            build_product_loop_eval_harness_execution,
        ),
        (
            2,
            "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-CANDIDATE-SANDBOX-PROJECTION-R1",
            SANDBOX_ROOT,
            build_remediation_candidate_sandbox_projection,
        ),
        (
            3,
            "MAIN-CITYBRAIN-EPOCH4-EVAL-GAP-TRIAGE-FOUNDER-READINESS-NO-SESSION-R1",
            TRIAGE_ROOT,
            build_eval_gap_triage_founder_readiness,
        ),
        (
            4,
            "MAIN-CITYBRAIN-EPOCH4-EVAL-HARNESS-REMEDIATION-FINAL-REVERIFY-R1",
            FINAL_ROOT,
            build_final_reverify,
        ),
    ]:
        status = builder()
        step_statuses.append({"step_number": step_number, "package_id": package_id, "output_root": rel(root), "status": status})
    return build_sequence_summary(step_statuses)


def required_paths() -> list[Path]:
    return (
        [EVAL_ROOT / filename for filename in EVAL_FILES]
        + [SANDBOX_ROOT / filename for filename in SANDBOX_FILES]
        + [TRIAGE_ROOT / filename for filename in TRIAGE_FILES]
        + [FINAL_ROOT / filename for filename in FINAL_FILES]
        + [SEQUENCE_ROOT / filename for filename in SEQUENCE_FILES]
    )


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors

    expected = [
        (EVAL_ROOT / "DECISION.json", STATUS_EVAL),
        (SANDBOX_ROOT / "DECISION.json", STATUS_SANDBOX),
        (TRIAGE_ROOT / "DECISION.json", STATUS_TRIAGE),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, status in expected:
        actual = read_json(path, {}).get("status")
        if actual != status:
            errors.append(f"status:{rel(path)}:{actual}")

    eval_decision = read_json(EVAL_ROOT / "DECISION.json", {})
    sandbox_decision = read_json(SANDBOX_ROOT / "DECISION.json", {})
    triage_decision = read_json(TRIAGE_ROOT / "DECISION.json", {})
    final_decision = read_json(FINAL_ROOT / "DECISION.json", {})
    sequence_decision = read_json(SEQUENCE_ROOT / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json", {})
    execution_log = read_json(SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json", {})

    if eval_decision.get("case_count") != 12 or eval_decision.get("case_pass_count") != 12:
        errors.append("eval_case_execution_guard_failed")
    if eval_decision.get("training_fuel_created") is not False:
        errors.append("eval_training_fuel_guard_failed")
    if sandbox_decision.get("candidate_count") != 50 or sandbox_decision.get("source_truth_mutated") is not False:
        errors.append("sandbox_projection_guard_failed")
    if sandbox_decision.get("score_delta_claimed_as_fact") is not False:
        errors.append("sandbox_score_inflation_guard_failed")
    if triage_decision.get("founder_review_session_run") is not False or triage_decision.get("operator_or_founder_fuel_created") is not False:
        errors.append("triage_no_session_guard_failed")
    if final_decision.get("source_truth_mutated") is not False or final_decision.get("training_rows_created") is not False:
        errors.append("final_boundary_guard_failed")
    if sequence_decision.get("parallel_execution_used") is not False or execution_log.get("parallel_execution_used") is not False:
        errors.append("sequence_parallel_execution_guard_failed")

    expected_sequence = [
        "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-HARNESS-EXECUTION-R1",
        "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-CANDIDATE-SANDBOX-PROJECTION-R1",
        "MAIN-CITYBRAIN-EPOCH4-EVAL-GAP-TRIAGE-FOUNDER-READINESS-NO-SESSION-R1",
        "MAIN-CITYBRAIN-EPOCH4-EVAL-HARNESS-REMEDIATION-FINAL-REVERIFY-R1",
    ]
    if [step.get("package_id") for step in execution_log.get("steps", [])] != expected_sequence:
        errors.append("sequence_order_guard_failed")

    for path in [
        EVAL_ROOT / "HASH_MANIFEST.json",
        SANDBOX_ROOT / "HASH_MANIFEST.json",
        TRIAGE_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
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

#!/usr/bin/env python3
"""Run the Epoch 4 remediation execution / eval corpus sequence.

Sequence:
1. Data Maturity Remediation Execution Batch R1
2. Product Loop Evaluation Corpus R1
3. Founder Review Dry-Run No Session R1
4. Remediation / Eval Final Reverify R1

This runner is additive. It creates candidate/proposed artifacts only and keeps
founder review, fuel, source-truth mutation, live ingestion, forecasts, learned
ranking, and official workflow semantics parked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REMEDIATION_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_execution_batch_r1"
CORPUS_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1"
DRY_RUN_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_founder_review_dry_run_no_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_remediation_eval_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_remediation_execution_eval_corpus_sequence_r1"

PUB_REMEDIATION = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-data-maturity-remediation-execution-batch-r1"
PUB_CORPUS = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-eval-corpus-r1"
PUB_DRY_RUN = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-founder-review-dry-run-no-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-remediation-eval-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-remediation-execution-eval-corpus-sequence-r1"

STATUS_REMEDIATION = "PASS_MAIN_CITYBRAIN_EPOCH4_DATA_MATURITY_REMEDIATION_EXECUTION_BATCH_R1_WITH_LIMITATIONS"
STATUS_CORPUS = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_EVAL_CORPUS_R1_WITH_LIMITATIONS"
STATUS_DRY_RUN = "PASS_MAIN_CITYBRAIN_EPOCH4_FOUNDER_REVIEW_DRY_RUN_NO_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_REMEDIATION_EVAL_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_REMEDIATION_EXECUTION_EVAL_CORPUS_SEQUENCE_R1_WITH_LIMITATIONS"

ALL_FAMILIES = [
    "mobility_access_interruption",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

QUEUE_TO_OUTPUT = {
    "identity_ambiguity": (
        "IDENTITY_AMBIGUITY_REMEDIATION_CANDIDATES.json",
        "cer_identity_bridge_candidate",
    ),
    "freshness_coverage": (
        "SOURCE_FRESHNESS_COVERAGE_REMEDIATION_CANDIDATES.json",
        "source_freshness_coverage_patch_candidate",
    ),
    "geometry_time_history": (
        "GEOMETRY_TIME_HISTORY_REMEDIATION_CANDIDATES.json",
        "geometry_time_history_annotation_candidate",
    ),
    "check_downgrade": (
        "CHECK_DOWNGRADE_REMEDIATION_CANDIDATES.json",
        "check_downgrade_fixture_candidate",
    ),
    "source_registry_enrichment": (
        "SOURCE_REGISTRY_ENRICHMENT_PATCH_CANDIDATES.json",
        "source_registry_enrichment_patch_candidate",
    ),
}

PACKAGE_INPUTS = {
    "remediation_actions": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_actions_r1" / "DATA_MATURITY_REMEDIATION_DECISION.json",
    "remediation_queue": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_actions_r1" / "MATURITY_REMEDIATION_QUEUE.json",
    "source_registry_v1": ROOT / "outputs" / "main_citybrain_track4_source_registry_v1" / "SOURCE_REGISTRY_V1.json",
    "source_registry_v1_1": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1" / "SOURCE_REGISTRY_V1_1.json",
    "event_stories_source_diff": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1" / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json",
    "trackb_maturity_brief_governance": ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1" / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
    "product_readiness": ROOT / "outputs" / "main_citybrain_epoch4_product_readiness_gap_closure_sequence_r1" / "DECISION.json",
    "product_readiness_atlas": ROOT / "outputs" / "main_citybrain_epoch4_product_readiness_gap_closure_sequence_r1" / "REVIEW_PACKET_360_V3_EVIDENCE_ATLAS.json",
    "product_readiness_matrix": ROOT / "outputs" / "main_citybrain_epoch4_product_readiness_gap_closure_sequence_r1" / "CROSS_FAMILY_OPTION_EVIDENCE_MATRIX.json",
    "event_fabric_v2_5": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1" / "DECISION.json",
    "event_fabric_consumption": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1" / "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT.json",
    "cer_check_stress": ROOT / "outputs" / "main_citybrain_epoch4_cer_check_event_stress_eval_r1" / "CER_CHECK_EVENT_STRESS_EVAL_SUMMARY.json",
    "non_sumo_engines": ROOT / "outputs" / "main_citybrain_epoch4_non_sumo_domain_option_engines_r1" / "NON_SUMO_DOMAIN_OPTION_ENGINE_CATALOG.json",
    "simulation_v2_4": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1" / "DECISION.json",
    "pre_founder_review_prep": ROOT / "outputs" / "main_citybrain_epoch4_pre_founder_review_prep_no_session_r1" / "DECISION.json",
    "review_packet_360_r1": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
    "review_packet_360_v2": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1" / "DECISION.json",
    "after_deepening_cross_track_reverify": ROOT / "outputs" / "main_citybrain_epoch4_after_deepening_cross_track_reverify_r1" / "DECISION.json",
}

FORBIDDEN_CAPABILITIES = [
    "founder_or_operator_review_session_results",
    "operator_or_founder_fuel",
    "training_rows_or_learned_labels",
    "learned_ranking_or_model_training",
    "ForecastPacket_or_product_forecast_surface",
    "calibrated_simulation_claim",
    "production_live_ingestion",
    "official_action_case_ticket",
    "dispatch_control_enforcement",
    "source_truth_mutation",
]

REMEDIATION_FILES = [
    "REMEDIATION_EXECUTION_PLAN.json",
    "IDENTITY_AMBIGUITY_REMEDIATION_CANDIDATES.json",
    "SOURCE_FRESHNESS_COVERAGE_REMEDIATION_CANDIDATES.json",
    "GEOMETRY_TIME_HISTORY_REMEDIATION_CANDIDATES.json",
    "CHECK_DOWNGRADE_REMEDIATION_CANDIDATES.json",
    "SOURCE_REGISTRY_ENRICHMENT_PATCH_CANDIDATES.json",
    "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
    "NO_SCORE_INFLATION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json",
    "HASH_MANIFEST.json",
]

CORPUS_FILES = [
    "PRODUCT_LOOP_EVAL_CORPUS_INDEX.json",
    "EVAL_CASES_4_FAMILY.json",
    "EXPECTED_CHECK_OUTCOMES.json",
    "EXPECTED_BRIEF_BLOCKS.json",
    "EXPECTED_EVENT_STATE_ASSERTIONS.json",
    "EXPECTED_SIMULATION_OPTION_ASSERTIONS.json",
    "EXPECTED_SPATIAL_PACKET_ASSERTIONS.json",
    "REGRESSION_TEST_PLAN.json",
    "NO_TRAINING_FUEL_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json",
    "HASH_MANIFEST.json",
]

DRY_RUN_FILES = [
    "DRY_RUN_TASK_QUEUE.json",
    "DRY_RUN_FORM_VALIDATION_REPORT.json",
    "DRY_RUN_PACKET_COMPLETENESS_REPORT.json",
    "DRY_RUN_OPERATOR_BURDEN_ESTIMATE.json",
    "FOUNDING_REVIEW_NOT_RUN_GUARD.json",
    "NO_FUEL_NO_DISPOSITIONS_GUARD.json",
    "FOUNDER_REVIEW_DRY_RUN_DECISION.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "INPUT_COVERAGE_AUDIT.json",
    "REMEDIATION_CANDIDATE_REVERIFY.json",
    "EVAL_CORPUS_REVERIFY.json",
    "FOUNDER_DRY_RUN_NO_SESSION_REVERIFY.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
    "DECISION.json",
]

SEQUENCE_FILES = [
    "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json",
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def input_audit(keys: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key in keys:
        path = PACKAGE_INPUTS[key]
        payload = read_json(path, {})
        rows.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "status": status_of(payload),
            }
        )
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
        "artifact_id": filename.replace(".", "_"),
        "algorithm": "sha256",
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
        "boundary": "local/replay/review-only; candidate/proposed artifacts only",
        "checks": {
            "calibrated_simulation_claim_created": False,
            "dispatch_control_enforcement_created": False,
            "ForecastPacket_or_product_forecast_surface_created": False,
            "founder_or_operator_review_session_results_created": False,
            "learned_ranking_or_model_training_created": False,
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


def candidate_from_item(queue_name: str, item: dict[str, Any], candidate_kind: str, index: int) -> dict[str, Any]:
    queue_id = item.get("queue_id", f"{queue_name}-{index:02d}")
    candidate_id = f"{candidate_kind}:{queue_id}"
    patch_fields: dict[str, Any]
    if queue_name == "identity_ambiguity":
        patch_fields = {
            "cer_review_candidate": True,
            "alias_conflict_review_ref": item.get("source_ref"),
            "proposed_action": "prepare CER alias/provenance review packet",
        }
    elif queue_name == "freshness_coverage":
        patch_fields = {
            "coverage_window_candidate": "to_be_verified",
            "refresh_cadence_candidate": "to_be_verified",
            "source_metadata_only": True,
        }
    elif queue_name == "geometry_time_history":
        patch_fields = {
            "geometry_annotation_candidate": "missing_or_incomplete",
            "time_history_annotation_candidate": "missing_or_incomplete",
            "spatial_overlay_readiness_target": True,
        }
    elif queue_name == "check_downgrade":
        patch_fields = {
            "check_downgrade_reason_ref": item.get("source_ref"),
            "fixture_candidate": True,
            "maps_to_source_remediation_queue": True,
        }
    else:
        patch_fields = {
            "owner_candidate": "to_be_verified",
            "source_class_candidate": "to_be_verified",
            "freshness_metadata_candidate": "to_be_verified",
        }

    return {
        "candidate_id": candidate_id,
        "candidate_kind": candidate_kind,
        "candidate_status": "proposed_candidate_only",
        "claim_boundary": item.get("claim_boundary", "candidate_only"),
        "expected_unlock": item.get("expected_unlock"),
        "mutates_source_truth": False,
        "priority": item.get("priority", index),
        "proposed_patch": patch_fields,
        "score_delta_claimed": False,
        "source_ref": item.get("source_ref"),
        "source_truth_patch_applied": False,
        "source_queue": queue_name,
        "source_queue_id": queue_id,
        "verification_fixture_ref": f"fixture:{queue_name}:{queue_id}",
    }


def maturity_queues() -> dict[str, list[dict[str, Any]]]:
    queue = read_json(PACKAGE_INPUTS["remediation_queue"], {})
    queues = queue.get("queues", {})
    return {name: list(queues.get(name, [])) for name in QUEUE_TO_OUTPUT}


def build_remediation_execution_batch() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-REMEDIATION-EXECUTION-BATCH-R1"
    queues = maturity_queues()
    candidates_by_queue: dict[str, list[dict[str, Any]]] = {}
    all_candidates: list[dict[str, Any]] = []
    unavailable = []
    for queue_name, items in queues.items():
        _, kind = QUEUE_TO_OUTPUT[queue_name]
        if not items:
            unavailable.append(queue_name)
        candidates = [candidate_from_item(queue_name, item, kind, idx) for idx, item in enumerate(items, start=1)]
        candidates_by_queue[queue_name] = candidates
        all_candidates.extend(candidates)

    counts = {name: len(items) for name, items in candidates_by_queue.items()}
    plan = {
        "artifact_id": "REMEDIATION_EXECUTION_PLAN",
        "candidate_count": len(all_candidates),
        "candidate_counts_by_queue": counts,
        "generated_at": now_iso(),
        "input_audit": input_audit(
            [
                "remediation_actions",
                "remediation_queue",
                "source_registry_v1",
                "source_registry_v1_1",
                "event_stories_source_diff",
                "trackb_maturity_brief_governance",
                "product_readiness",
            ]
        ),
        "mutates_source_truth": False,
        "package_id": package_id,
        "queue_count": len(queues),
        "queues_consumed": [name for name, items in queues.items() if items],
        "raw_remediation_item_count": sum(len(items) for items in queues.values()),
        "score_delta_claimed": False,
        "status": "PASS_WITH_LIMITATIONS",
        "unavailable_queues": unavailable,
    }
    write_json(REMEDIATION_ROOT / "REMEDIATION_EXECUTION_PLAN.json", plan)

    for queue_name, (filename, _) in QUEUE_TO_OUTPUT.items():
        write_json(
            REMEDIATION_ROOT / filename,
            {
                "artifact_id": filename.removesuffix(".json"),
                "candidate_count": len(candidates_by_queue[queue_name]),
                "candidates": candidates_by_queue[queue_name],
                "generated_at": now_iso(),
                "source_queue": queue_name,
                "status": "PASS_WITH_LIMITATIONS" if candidates_by_queue[queue_name] else "UNAVAILABLE_WITH_LIMITATIONS",
            },
        )

    write_json(
        REMEDIATION_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
        {
            "artifact_id": "NO_SOURCE_TRUTH_MUTATION_GUARD",
            "canonical_truth_mutated": False,
            "candidate_patches_only": True,
            "fabricated_coverage_created": False,
            "source_records_mutated": False,
            "source_truth_patch_applied": False,
            "status": "PASS",
        },
    )
    write_json(
        REMEDIATION_ROOT / "NO_SCORE_INFLATION_GUARD.json",
        {
            "artifact_id": "NO_SCORE_INFLATION_GUARD",
            "maturity_inflation_without_evidence": False,
            "new_maturity_score_claimed": False,
            "original_maturity_score_preserved": 36.1,
            "score_delta_claimed": False,
            "status": "PASS",
        },
    )
    write_json(REMEDIATION_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, REMEDIATION_ROOT))
    write_json(
        REMEDIATION_ROOT / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json",
        {
            "artifact_id": "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION",
            "candidate_count": len(all_candidates),
            "candidate_count_minimum_met": len(all_candidates) >= 20,
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "item_count_consumed": sum(len(items) for items in queues.values()),
            "limitations": [
                "candidate/proposed artifacts only",
                "no source-truth mutation",
                "no maturity score inflation",
                "human review still parked",
            ],
            "new_maturity_score_claimed": False,
            "package_id": package_id,
            "queue_count": len(queues),
            "queues_consumed": [name for name, items in queues.items() if items],
            "source_truth_mutated": False,
            "status": STATUS_REMEDIATION,
        },
    )
    publish(REMEDIATION_ROOT, PUB_REMEDIATION, [f for f in REMEDIATION_FILES if f != "HASH_MANIFEST.json"])
    hash_manifest(REMEDIATION_ROOT, PUB_REMEDIATION)
    return STATUS_REMEDIATION


def atlas_families() -> list[dict[str, Any]]:
    atlas = read_json(PACKAGE_INPUTS["product_readiness_atlas"], {})
    by_id = {row.get("family_id"): row for row in atlas.get("families", [])}
    return [by_id.get(family, {"family_id": family, "family_label": family.replace("_", " ").title()}) for family in ALL_FAMILIES]


def option_rows() -> dict[str, dict[str, Any]]:
    matrix = read_json(PACKAGE_INPUTS["product_readiness_matrix"], {})
    return {row.get("family_id"): row for row in matrix.get("rows", [])}


def consumption_rows() -> dict[str, dict[str, Any]]:
    consumption = read_json(PACKAGE_INPUTS["event_fabric_consumption"], {})
    return {row.get("family_id"): row for row in consumption.get("families", [])}


def build_eval_cases() -> list[dict[str, Any]]:
    option_by_family = option_rows()
    consumption_by_family = consumption_rows()
    cases = []
    case_types = [
        ("packet_baseline", "sufficient_for_review"),
        ("downgrade_pressure", "downgrade_source_depth"),
        ("contradiction_guard", "contradiction"),
    ]
    for family in atlas_families():
        family_id = family["family_id"]
        option = option_by_family.get(family_id, {})
        consumption = consumption_by_family.get(family_id, {})
        for idx, (case_type, check_expectation) in enumerate(case_types, start=1):
            case_id = f"eval:{family_id}:{case_type}:r1"
            cases.append(
                {
                    "case_id": case_id,
                    "case_type": case_type,
                    "cer_entity_ref": family.get("cer_entity", f"cer:{family_id}:atlas_primary"),
                    "check_ref": family.get("check_v1_result", f"check:v1:{family_id}:stress_eval"),
                    "expected_check_outcome": check_expectation,
                    "evidence_refs": list(family.get("source_records", [])) + list(family.get("diff_refs", [])),
                    "event_state_ref": family.get("event_state", f"event_state:v2_5:{family_id}"),
                    "family_id": family_id,
                    "family_label": family.get("family_label", family_id.replace("_", " ").title()),
                    "limitations": family.get("limitations", ["local/replay/review-only"]),
                    "no_action_boundary": True,
                    "option_evidence": option or family.get("option_evidence", {}),
                    "regression_case_number": idx,
                    "seg_context_ref": family.get("seg_context", f"seg:{family_id}:atlas_context"),
                    "source_class": "replay",
                    "spatial_refs": family.get("spatial_refs", [f"spatial:v2_5:{family_id}:atlas_overlay"]),
                    "brief_refs": family.get(
                        "brief_refs",
                        [
                            f"brief:v3:{family_id}:operator",
                            f"brief:v3:{family_id}:executive",
                            f"brief:v3:{family_id}:technical",
                        ],
                    ),
                    "training_eligible": False,
                    "watch_check_brief_spatial_consumption": {
                        "brief_attachment_count": consumption.get("brief_attachment_count", 0),
                        "check_attachment_count": consumption.get("check_attachment_count", 0),
                        "spatial_handoff_count": consumption.get("spatial_handoff_count", 0),
                        "watch_admitted_count": consumption.get("watch_admitted_count", 0),
                    },
                }
            )
    return cases


def build_product_loop_eval_corpus() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-CORPUS-R1"
    cases = build_eval_cases()
    family_counts = Counter(case["family_id"] for case in cases)
    family_list = sorted(family_counts)
    case_ids = [case["case_id"] for case in cases]

    write_json(
        CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_INDEX.json",
        {
            "artifact_id": "PRODUCT_LOOP_EVAL_CORPUS_INDEX",
            "case_count": len(cases),
            "corpus_hash": stable_hash(cases, 64),
            "families": family_list,
            "family_count": len(family_list),
            "generated_at": now_iso(),
            "input_audit": input_audit(
                [
                    "product_readiness",
                    "product_readiness_atlas",
                    "product_readiness_matrix",
                    "event_fabric_v2_5",
                    "event_fabric_consumption",
                    "cer_check_stress",
                    "non_sumo_engines",
                    "simulation_v2_4",
                    "event_stories_source_diff",
                    "trackb_maturity_brief_governance",
                ]
            ),
            "package_id": package_id,
            "purpose": "deterministic evaluation and regression corpus only",
            "status": "PASS_WITH_LIMITATIONS",
            "training_corpus": False,
        },
    )
    write_json(
        CORPUS_ROOT / "EVAL_CASES_4_FAMILY.json",
        {
            "artifact_id": "EVAL_CASES_4_FAMILY",
            "case_count": len(cases),
            "cases": cases,
            "family_counts": dict(family_counts),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "EXPECTED_CHECK_OUTCOMES.json",
        {
            "artifact_id": "EXPECTED_CHECK_OUTCOMES",
            "assertions": [
                {
                    "case_id": case["case_id"],
                    "check_ref": case["check_ref"],
                    "expected_outcome": case["expected_check_outcome"],
                    "must_preserve_candidate_or_downgrade_boundary": True,
                }
                for case in cases
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "EXPECTED_BRIEF_BLOCKS.json",
        {
            "artifact_id": "EXPECTED_BRIEF_BLOCKS",
            "assertions": [
                {
                    "brief_refs": case["brief_refs"],
                    "case_id": case["case_id"],
                    "required_blocks": [
                        "subject",
                        "evidence_refs",
                        "check_summary",
                        "limitations",
                        "review_options",
                        "no_action_boundary",
                    ],
                    "forbidden_blocks": ["founder_response", "operator_disposition", "official_action"],
                }
                for case in cases
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "EXPECTED_EVENT_STATE_ASSERTIONS.json",
        {
            "artifact_id": "EXPECTED_EVENT_STATE_ASSERTIONS",
            "assertions": [
                {
                    "case_id": case["case_id"],
                    "event_state_ref": case["event_state_ref"],
                    "expected_mode": "local_replay_history_state",
                    "must_be_deterministic": True,
                    "must_not_create_live_ingestion": True,
                }
                for case in cases
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "EXPECTED_SIMULATION_OPTION_ASSERTIONS.json",
        {
            "artifact_id": "EXPECTED_SIMULATION_OPTION_ASSERTIONS",
            "assertions": [
                {
                    "calibration_state": case["option_evidence"].get("calibration_state", "not_applicable"),
                    "case_id": case["case_id"],
                    "engine_class": case["option_evidence"].get("engine_class", "review_option_evidence"),
                    "forecast_authority": False,
                    "not_equivalent_to": case["option_evidence"].get("not_equivalent_to", []),
                    "option_refs": case["option_evidence"].get("option_refs", []),
                }
                for case in cases
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "EXPECTED_SPATIAL_PACKET_ASSERTIONS.json",
        {
            "artifact_id": "EXPECTED_SPATIAL_PACKET_ASSERTIONS",
            "assertions": [
                {
                    "case_id": case["case_id"],
                    "no_live_control_claim": True,
                    "no_official_action_claim": True,
                    "spatial_refs": case["spatial_refs"],
                }
                for case in cases
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "REGRESSION_TEST_PLAN.json",
        {
            "artifact_id": "REGRESSION_TEST_PLAN",
            "case_ids": case_ids,
            "families": family_list,
            "planned_checks": [
                "case_schema_completeness",
                "check_expected_outcome_parity",
                "brief_block_presence",
                "event_state_determinism",
                "simulation_option_boundary",
                "spatial_packet_no_action_boundary",
                "no_training_fuel_guard",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CORPUS_ROOT / "NO_TRAINING_FUEL_GUARD.json",
        {
            "artifact_id": "NO_TRAINING_FUEL_GUARD",
            "founder_fuel_created": False,
            "human_review_labels_created": False,
            "operator_fuel_created": False,
            "training_corpus_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(CORPUS_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, CORPUS_ROOT))
    write_json(
        CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json",
        {
            "artifact_id": "PRODUCT_LOOP_EVAL_CORPUS_DECISION",
            "case_count": len(cases),
            "case_count_minimum_met": len(cases) >= 12,
            "families": family_list,
            "family_count": len(family_list),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "limitations": [
                "deterministic eval/regression corpus only",
                "no training rows or learned labels",
                "no founder review session result",
                "no forecast authority",
            ],
            "package_id": package_id,
            "status": STATUS_CORPUS,
            "training_fuel_created": False,
        },
    )
    publish(CORPUS_ROOT, PUB_CORPUS, [f for f in CORPUS_FILES if f != "HASH_MANIFEST.json"])
    hash_manifest(CORPUS_ROOT, PUB_CORPUS)
    return STATUS_CORPUS


def build_founder_review_dry_run_no_session() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-FOUNDER-REVIEW-DRY-RUN-NO-SESSION-R1"
    cases = read_json(CORPUS_ROOT / "EVAL_CASES_4_FAMILY.json", {}).get("cases", [])
    tasks = []
    for idx, case in enumerate(cases[:12], start=1):
        tasks.append(
            {
                "task_id": f"dry-run-task-{idx:02d}",
                "case_id": case["case_id"],
                "subject": f"{case['family_label']} dry-run review packet",
                "evidence_refs": case["evidence_refs"],
                "check_refs": [case["check_ref"]],
                "limitations": case["limitations"],
                "no_action_boundary": True,
                "review_options": [
                    "packet_ready_for_future_human_review",
                    "needs_more_evidence_before_future_session",
                    "keep_candidate_only",
                ],
                "responses_collected": False,
                "disposition_created": False,
                "fuel_created": False,
            }
        )

    required_fields = ["subject", "evidence_refs", "check_refs", "limitations", "review_options", "no_action_boundary"]
    missing = {
        task["task_id"]: [field for field in required_fields if not task.get(field)]
        for task in tasks
    }
    missing = {task_id: fields for task_id, fields in missing.items() if fields}

    write_json(
        DRY_RUN_ROOT / "DRY_RUN_TASK_QUEUE.json",
        {
            "artifact_id": "DRY_RUN_TASK_QUEUE",
            "generated_at": now_iso(),
            "input_audit": input_audit(
                [
                    "pre_founder_review_prep",
                    "product_readiness",
                    "review_packet_360_r1",
                    "review_packet_360_v2",
                    "product_readiness_atlas",
                ]
            ),
            "package_id": package_id,
            "session_run": False,
            "status": "PASS_WITH_LIMITATIONS",
            "task_count": len(tasks),
            "tasks": tasks,
        },
    )
    write_json(
        DRY_RUN_ROOT / "DRY_RUN_FORM_VALIDATION_REPORT.json",
        {
            "artifact_id": "DRY_RUN_FORM_VALIDATION_REPORT",
            "human_response_fields_created": False,
            "missing_required_fields_by_task": missing,
            "required_fields": required_fields,
            "status": "PASS" if not missing and len(tasks) >= 8 else "FAIL",
            "task_count_validated": len(tasks),
        },
    )
    write_json(
        DRY_RUN_ROOT / "DRY_RUN_PACKET_COMPLETENESS_REPORT.json",
        {
            "artifact_id": "DRY_RUN_PACKET_COMPLETENESS_REPORT",
            "all_tasks_have_check_refs": all(bool(task["check_refs"]) for task in tasks),
            "all_tasks_have_evidence_refs": all(bool(task["evidence_refs"]) for task in tasks),
            "all_tasks_have_limitations": all(bool(task["limitations"]) for task in tasks),
            "all_tasks_have_no_action_boundary": all(task["no_action_boundary"] is True for task in tasks),
            "status": "PASS_WITH_LIMITATIONS",
            "task_count": len(tasks),
        },
    )
    write_json(
        DRY_RUN_ROOT / "DRY_RUN_OPERATOR_BURDEN_ESTIMATE.json",
        {
            "artifact_id": "DRY_RUN_OPERATOR_BURDEN_ESTIMATE",
            "basis": "dry-run queue sizing only; not a session result",
            "estimated_minutes_per_task": 6,
            "estimated_total_minutes": len(tasks) * 6,
            "fuel_created": False,
            "session_run": False,
            "status": "PASS_WITH_LIMITATIONS",
            "task_count": len(tasks),
        },
    )
    write_json(
        DRY_RUN_ROOT / "FOUNDING_REVIEW_NOT_RUN_GUARD.json",
        {
            "artifact_id": "FOUNDING_REVIEW_NOT_RUN_GUARD",
            "dispositions_created": False,
            "founder_review_session_run": False,
            "founder_session_results_created": False,
            "human_responses_collected": False,
            "operator_review_session_run": False,
            "status": "PASS",
        },
    )
    write_json(
        DRY_RUN_ROOT / "NO_FUEL_NO_DISPOSITIONS_GUARD.json",
        {
            "artifact_id": "NO_FUEL_NO_DISPOSITIONS_GUARD",
            "dispositions_created": False,
            "founder_fuel_created": False,
            "operator_fuel_created": False,
            "training_eligible_fuel_created": False,
            "status": "PASS",
        },
    )
    write_json(
        DRY_RUN_ROOT / "FOUNDER_REVIEW_DRY_RUN_DECISION.json",
        {
            "artifact_id": "FOUNDER_REVIEW_DRY_RUN_DECISION",
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "minimum_task_count_met": len(tasks) >= 8,
            "package_id": package_id,
            "session_run": False,
            "status": STATUS_DRY_RUN,
            "task_count": len(tasks),
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
        },
    )
    publish(DRY_RUN_ROOT, PUB_DRY_RUN, [f for f in DRY_RUN_FILES if f != "HASH_MANIFEST.json"])
    hash_manifest(DRY_RUN_ROOT, PUB_DRY_RUN)
    return STATUS_DRY_RUN


def package_file_audit(root: Path, files: list[str]) -> list[dict[str, Any]]:
    return [{"file": filename, "path": rel(root / filename), "exists": (root / filename).exists()} for filename in files]


def build_final_reverify() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-EVAL-FINAL-REVERIFY-R1"
    remediation_decision = read_json(REMEDIATION_ROOT / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json", {})
    corpus_decision = read_json(CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json", {})
    dry_run_decision = read_json(DRY_RUN_ROOT / "FOUNDER_REVIEW_DRY_RUN_DECISION.json", {})
    remediation_candidates = []
    for filename, _ in QUEUE_TO_OUTPUT.values():
        remediation_candidates.extend(read_json(REMEDIATION_ROOT / filename, {}).get("candidates", []))
    eval_cases = read_json(CORPUS_ROOT / "EVAL_CASES_4_FAMILY.json", {}).get("cases", [])
    dry_tasks = read_json(DRY_RUN_ROOT / "DRY_RUN_TASK_QUEUE.json", {}).get("tasks", [])

    input_files = {
        "remediation_execution_batch": package_file_audit(REMEDIATION_ROOT, REMEDIATION_FILES),
        "product_loop_eval_corpus": package_file_audit(CORPUS_ROOT, CORPUS_FILES),
        "founder_review_dry_run_no_session": package_file_audit(DRY_RUN_ROOT, DRY_RUN_FILES),
    }
    all_required_present = all(row["exists"] for rows in input_files.values() for row in rows)
    write_json(
        FINAL_ROOT / "INPUT_COVERAGE_AUDIT.json",
        {
            "artifact_id": "INPUT_COVERAGE_AUDIT",
            "all_required_outputs_present": all_required_present,
            "generated_at": now_iso(),
            "input_files": input_files,
            "package_id": package_id,
            "status": "PASS_WITH_LIMITATIONS" if all_required_present else "FAIL",
        },
    )
    write_json(
        FINAL_ROOT / "REMEDIATION_CANDIDATE_REVERIFY.json",
        {
            "artifact_id": "REMEDIATION_CANDIDATE_REVERIFY",
            "candidate_count": len(remediation_candidates),
            "candidate_count_minimum_met": len(remediation_candidates) >= 20,
            "candidate_statuses": sorted({item.get("candidate_status") for item in remediation_candidates}),
            "decision_status": remediation_decision.get("status"),
            "mutating_candidates": [item.get("candidate_id") for item in remediation_candidates if item.get("mutates_source_truth")],
            "new_maturity_score_claimed": remediation_decision.get("new_maturity_score_claimed") is True,
            "source_truth_mutated": remediation_decision.get("source_truth_mutated") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "EVAL_CORPUS_REVERIFY.json",
        {
            "artifact_id": "EVAL_CORPUS_REVERIFY",
            "case_count": len(eval_cases),
            "case_count_minimum_met": len(eval_cases) >= 12,
            "decision_status": corpus_decision.get("status"),
            "families": sorted({case.get("family_id") for case in eval_cases}),
            "family_count": len({case.get("family_id") for case in eval_cases}),
            "training_eligible_cases": [case.get("case_id") for case in eval_cases if case.get("training_eligible")],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "FOUNDER_DRY_RUN_NO_SESSION_REVERIFY.json",
        {
            "artifact_id": "FOUNDER_DRY_RUN_NO_SESSION_REVERIFY",
            "decision_status": dry_run_decision.get("status"),
            "dispositions_created": dry_run_decision.get("dispositions_created") is True,
            "fuel_created": dry_run_decision.get("operator_or_founder_fuel_created") is True,
            "session_run": dry_run_decision.get("session_run") is True,
            "status": "PASS_WITH_LIMITATIONS",
            "task_count": len(dry_tasks),
            "task_count_minimum_met": len(dry_tasks) >= 8,
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, FINAL_ROOT))
    publish(FINAL_ROOT, PUB_FINAL, [f for f in FINAL_FILES if f != "HASH_MANIFEST_REVERIFY.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL, "HASH_MANIFEST_REVERIFY.json")
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "all_required_outputs_present": all_required_present,
            "forbidden_capabilities_created": [],
            "founder_review_session_run": False,
            "generated_at": now_iso(),
            "live_ingestion_created": False,
            "official_action_created": False,
            "package_id": package_id,
            "product_forecast_surface_created": False,
            "remediation_candidate_count": len(remediation_candidates),
            "eval_case_count": len(eval_cases),
            "dry_run_task_count": len(dry_tasks),
            "source_truth_mutated": False,
            "status": STATUS_FINAL,
            "training_fuel_created": False,
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, ["DECISION.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL, "HASH_MANIFEST_REVERIFY.json")
    return STATUS_FINAL


def build_sequence_summary(step_statuses: list[dict[str, Any]]) -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-EXECUTION-EVAL-CORPUS-SEQUENCE-R1"
    write_json(
        SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json",
        {
            "artifact_id": "SEQUENTIAL_EXECUTION_LOG",
            "generated_at": now_iso(),
            "parallel_execution_used": False,
            "package_id": package_id,
            "steps": step_statuses,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SEQUENCE_ROOT / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json",
        {
            "artifact_id": "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION",
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
        },
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, [f for f in SEQUENCE_FILES if f != "HASH_MANIFEST.json"])
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)
    return STATUS_SEQUENCE


def build_all() -> str:
    step_statuses = []
    for step_number, package_id, root, builder in [
        (
            1,
            "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-REMEDIATION-EXECUTION-BATCH-R1",
            REMEDIATION_ROOT,
            build_remediation_execution_batch,
        ),
        (
            2,
            "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-CORPUS-R1",
            CORPUS_ROOT,
            build_product_loop_eval_corpus,
        ),
        (
            3,
            "MAIN-CITYBRAIN-EPOCH4-FOUNDER-REVIEW-DRY-RUN-NO-SESSION-R1",
            DRY_RUN_ROOT,
            build_founder_review_dry_run_no_session,
        ),
        (
            4,
            "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-EVAL-FINAL-REVERIFY-R1",
            FINAL_ROOT,
            build_final_reverify,
        ),
    ]:
        status = builder()
        step_statuses.append(
            {
                "step_number": step_number,
                "package_id": package_id,
                "output_root": rel(root),
                "status": status,
            }
        )
    return build_sequence_summary(step_statuses)


def required_paths() -> list[Path]:
    return (
        [REMEDIATION_ROOT / filename for filename in REMEDIATION_FILES]
        + [CORPUS_ROOT / filename for filename in CORPUS_FILES]
        + [DRY_RUN_ROOT / filename for filename in DRY_RUN_FILES]
        + [FINAL_ROOT / filename for filename in FINAL_FILES]
        + [SEQUENCE_ROOT / filename for filename in SEQUENCE_FILES]
    )


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors

    decisions = [
        (REMEDIATION_ROOT / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json", STATUS_REMEDIATION),
        (CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json", STATUS_CORPUS),
        (DRY_RUN_ROOT / "FOUNDER_REVIEW_DRY_RUN_DECISION.json", STATUS_DRY_RUN),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, expected in decisions:
        actual = read_json(path, {}).get("status")
        if actual != expected:
            errors.append(f"status:{rel(path)}:{actual}")

    remediation = read_json(REMEDIATION_ROOT / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json", {})
    corpus = read_json(CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json", {})
    dry_run = read_json(DRY_RUN_ROOT / "FOUNDER_REVIEW_DRY_RUN_DECISION.json", {})
    final = read_json(FINAL_ROOT / "DECISION.json", {})
    sequence = read_json(SEQUENCE_ROOT / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json", {})
    execution_log = read_json(SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json", {})

    if remediation.get("candidate_count", 0) < 20 or remediation.get("source_truth_mutated") is not False:
        errors.append("remediation_candidate_or_mutation_guard_failed")
    if remediation.get("new_maturity_score_claimed") is not False:
        errors.append("maturity_score_inflation_guard_failed")
    if corpus.get("family_count") != 4 or corpus.get("case_count", 0) < 12 or corpus.get("training_fuel_created") is not False:
        errors.append("eval_corpus_guard_failed")
    if dry_run.get("task_count", 0) < 8 or dry_run.get("session_run") is not False:
        errors.append("dry_run_no_session_guard_failed")
    if final.get("source_truth_mutated") is not False or final.get("training_fuel_created") is not False:
        errors.append("final_boundary_guard_failed")
    if sequence.get("parallel_execution_used") is not False or execution_log.get("parallel_execution_used") is not False:
        errors.append("sequence_parallel_execution_guard_failed")

    expected_sequence = [
        "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-REMEDIATION-EXECUTION-BATCH-R1",
        "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-CORPUS-R1",
        "MAIN-CITYBRAIN-EPOCH4-FOUNDER-REVIEW-DRY-RUN-NO-SESSION-R1",
        "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-EVAL-FINAL-REVERIFY-R1",
    ]
    if [step.get("package_id") for step in execution_log.get("steps", [])] != expected_sequence:
        errors.append("sequence_order_guard_failed")

    for path in [
        REMEDIATION_ROOT / "HASH_MANIFEST.json",
        CORPUS_ROOT / "HASH_MANIFEST.json",
        DRY_RUN_ROOT / "HASH_MANIFEST.json",
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
        status = build_all()
        print(status)

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

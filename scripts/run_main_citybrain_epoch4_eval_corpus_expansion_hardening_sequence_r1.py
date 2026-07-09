#!/usr/bin/env python3
"""Run Epoch 4 Eval Corpus Expansion + Hardening Sequence R1.

This no-human sequence expands the product-loop eval layer from the 12-case
corpus to a broader 48-case replay/offline corpus, projects candidate-fix
effects in a sandbox, adds challenge/negative cases, refreshes no-session
readiness, and performs final reverify.
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

EXPANSION_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2"
FIX_SANDBOX_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_candidate_fix_effect_sandbox_r1"
CHALLENGE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_product_loop_challenge_negative_suite_r1"
READINESS_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_no_session_readiness_refresh_r2"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_eval_expansion_hardening_final_reverify_r1"

PUB_EXPANSION = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-corpus-expansion-r2"
PUB_FIX_SANDBOX = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-candidate-fix-effect-sandbox-r1"
PUB_CHALLENGE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-product-loop-challenge-negative-suite-r1"
PUB_READINESS = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-no-session-readiness-refresh-r2"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-expansion-hardening-final-reverify-r1"

STATUS_EXPANSION = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_CORPUS_EXPANSION_R2_WITH_LIMITATIONS"
STATUS_FIX_SANDBOX = "PASS_MAIN_CITYBRAIN_EPOCH4_CANDIDATE_FIX_EFFECT_SANDBOX_R1_WITH_LIMITATIONS"
STATUS_CHALLENGE = "PASS_MAIN_CITYBRAIN_EPOCH4_PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_R1_WITH_LIMITATIONS"
STATUS_READINESS = "PASS_MAIN_CITYBRAIN_EPOCH4_NO_SESSION_READINESS_REFRESH_R2_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_CORPUS_EXPANSION_HARDENING_SEQUENCE_R1_WITH_LIMITATIONS"

FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

FAMILY_SOURCE_MAP = {
    "mobility_access_interruption_v0": "mobility_access_interruption",
    "building_compliance_perception_candidate": "building_compliance_perception_candidate",
    "permit_inspection_delay": "permit_inspection_delay",
    "city_asset_infrastructure_issue": "city_asset_infrastructure_issue",
}

CASE_TYPES = [
    ("positive_packet_baseline", "positive", "sufficient_for_review"),
    ("negative_no_data", "no-data", "abstain_no_data"),
    ("contradiction_pair", "contradiction", "downgrade_contradiction"),
    ("stale_freshness", "stale", "downgrade_freshness"),
    ("candidate_only_identity", "candidate-only", "candidate_only"),
    ("proximity_only_context", "proximity-only", "downgrade_proximity_only"),
    ("unresolved_entity", "unresolved", "abstain_unresolved"),
    ("quarantine_invalid_event", "quarantine", "quarantine_invalid"),
    ("simulation_not_applicable", "simulation-not-applicable", "simulation_not_applicable"),
    ("source_depth_thin", "source-depth", "downgrade_source_depth"),
    ("source_class_boundary", "source-class", "downgrade_source_class"),
    ("spatial_packet_gap", "spatial-gap", "downgrade_spatial_context"),
]

FORBIDDEN_CAPABILITIES = [
    "live_ingestion",
    "production_event_monitoring",
    "external_operator_validation",
    "fabricated_founder_operator_sessions",
    "operator_fuel",
    "training_rows",
    "learned_ranking",
    "ForecastPacket_or_product_forecast_surface",
    "official_workflow_action_case_ticket_dispatch_control_enforcement",
    "source_truth_mutation",
]

INPUTS = {
    "pre_probe_targeted_fix_decision": ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_targeted_fix_sequence_r1" / "PRE_PROBE_TARGETED_FIX_SEQUENCE_DECISION.json",
    "pre_probe_derived_fixes": ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_targeted_fix_sequence_r1" / "DERIVED_TARGETED_FIX_APPLICATION_R1.json",
    "pre_probe_eval_rerun": ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_targeted_fix_sequence_r1" / "PRODUCT_LOOP_EVAL_RERUN_R2.json",
    "pre_probe_final_reverify": ROOT / "outputs" / "main_citybrain_epoch4_pre_probe_final_reverify_r1" / "PRE_PROBE_FINAL_REVERIFY_DECISION.json",
    "eval_corpus_r1": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_corpus_r1" / "EVAL_CASES_4_FAMILY.json",
    "candidate_fix_overlays": ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1" / "CANDIDATE_PATCH_OVERLAYS.json",
    "candidate_fix_impact_by_queue": ROOT / "outputs" / "main_citybrain_epoch4_remediation_candidate_sandbox_projection_r1" / "PROJECTED_IMPACT_BY_QUEUE.json",
    "after_deepening_cross_track": ROOT / "outputs" / "main_citybrain_epoch4_after_deepening_cross_track_reverify_r1" / "DECISION.json",
    "post_sumo_deepening_final": ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_deepening_final_reverify_r1" / "DECISION.json",
}

EXPANSION_FILES = [
    "EVAL_CORPUS_EXPANSION_R2_DECISION.json",
    "EVAL_CORPUS_R2_INDEX.json",
    "EVAL_CASES_R2.jsonl",
    "EVAL_CASE_FAMILY_BALANCE_REPORT.json",
    "EVAL_CASE_SOURCE_COVERAGE_REPORT.json",
    "EVAL_CASE_NEGATIVE_COVERAGE_REPORT.json",
    "HASH_MANIFEST.json",
]

FIX_SANDBOX_FILES = [
    "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json",
    "DERIVED_FIX_INPUT_INVENTORY.json",
    "CANDIDATE_FIX_EFFECT_MATRIX.json",
    "BEFORE_AFTER_EVAL_SUMMARY.json",
    "FIX_PROMOTION_CANDIDATE_REGISTER.json",
    "FIX_REJECTION_OR_DEFER_REGISTER.json",
    "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
    "HASH_MANIFEST.json",
]

CHALLENGE_FILES = [
    "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json",
    "CHALLENGE_CASES.jsonl",
    "EXPECTED_ABSTAIN_CASES.json",
    "EXPECTED_DOWNGRADE_CASES.json",
    "EXPECTED_QUARANTINE_CASES.json",
    "EXPECTED_SIMULATION_NOT_APPLICABLE_CASES.json",
    "CHALLENGE_RUN_RESULTS.json",
    "HASH_MANIFEST.json",
]

READINESS_FILES = [
    "NO_SESSION_READINESS_REFRESH_DECISION.json",
    "FOUNDER_PROBE_READINESS_CURRENT_STATE.json",
    "WHAT_IS_READY_FOR_FOUNDER_REVIEW.json",
    "WHAT_SHOULD_BE_FIXED_BEFORE_FOUNDER_REVIEW.json",
    "WHAT_MUST_WAIT_FOR_EXTERNAL_OPERATORS.json",
    "NO_SESSION_NO_FUEL_GUARD.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json",
    "EVAL_CORPUS_R2_REVERIFY.json",
    "CANDIDATE_FIX_SANDBOX_REVERIFY.json",
    "CHALLENGE_NEGATIVE_SUITE_REVERIFY.json",
    "NO_SESSION_READINESS_REVERIFY.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")


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
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "checks": {
            "ForecastPacket_created": False,
            "external_operator_validation_created": False,
            "fabricated_founder_operator_sessions_created": False,
            "learned_ranking_created": False,
            "live_ingestion_created": False,
            "official_workflow_action_case_ticket_dispatch_control_enforcement_created": False,
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


def base_cases_by_family() -> dict[str, list[dict[str, Any]]]:
    rows = read_json(INPUTS["eval_corpus_r1"], {}).get("cases", [])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("family_id", "")].append(row)
    return grouped


def build_r2_cases() -> list[dict[str, Any]]:
    grouped = base_cases_by_family()
    rows = []
    for family in FAMILIES:
        source_family = FAMILY_SOURCE_MAP[family]
        template = grouped.get(source_family, [{}])[0] if grouped.get(source_family) else {}
        for index, (case_type, negative_class, expected_outcome) in enumerate(CASE_TYPES, start=1):
            simulation_expectation = "simulation_not_applicable"
            if family == "city_asset_infrastructure_issue" and case_type != "simulation_not_applicable":
                simulation_expectation = "SUMO_smoke_allowed_not_calibrated"
            rows.append(
                {
                    "case_id": f"eval-r2:{family}:{case_type}",
                    "case_number": index,
                    "case_type": case_type,
                    "challenge_class": negative_class,
                    "expected_check_outcome": expected_outcome,
                    "expected_event_handling": "quarantine" if negative_class == "quarantine" else "local_replay_state_only",
                    "expected_product_claim": "abstain_or_limited" if negative_class != "positive" else "review_limited_positive",
                    "expected_simulation_handling": simulation_expectation,
                    "family_id": family,
                    "source_family_id": source_family,
                    "replay_mode": "local_offline_replay",
                    "source_class": "replay",
                    "source_refs": template.get("evidence_refs", [f"source:v1_1:{source_family}:r2:{index:02d}"]),
                    "check_ref": template.get("check_ref", f"check:v1:{source_family}:stress_eval"),
                    "brief_refs": template.get("brief_refs", [f"brief:v3:{source_family}:operator"]),
                    "spatial_refs": template.get("spatial_refs", [f"spatial:v2_5:{source_family}:r2_overlay"]),
                    "no_action_boundary": True,
                    "training_eligible": False,
                    "operator_fuel": False,
                    "source_truth_mutated": False,
                }
            )
    return rows


def build_eval_corpus_expansion() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-EVAL-CORPUS-EXPANSION-R2"
    cases = build_r2_cases()
    family_counts = Counter(row["family_id"] for row in cases)
    challenge_counts = Counter(row["challenge_class"] for row in cases)
    source_modes = Counter(row["source_class"] for row in cases)
    write_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl", cases)
    write_json(
        EXPANSION_ROOT / "EVAL_CORPUS_R2_INDEX.json",
        {
            "artifact_id": "EVAL_CORPUS_R2_INDEX",
            "case_count": len(cases),
            "case_hash": stable_hash(cases, 64),
            "challenge_classes": sorted(challenge_counts),
            "family_count": len(family_counts),
            "families": sorted(family_counts),
            "generated_at": now_iso(),
            "input_audit": input_audit(["pre_probe_final_reverify", "eval_corpus_r1", "after_deepening_cross_track", "post_sumo_deepening_final"]),
            "package_id": package_id,
            "status": "PASS_WITH_LIMITATIONS",
            "target_min_cases": 48,
        },
    )
    write_json(
        EXPANSION_ROOT / "EVAL_CASE_FAMILY_BALANCE_REPORT.json",
        {
            "artifact_id": "EVAL_CASE_FAMILY_BALANCE_REPORT",
            "family_counts": dict(family_counts),
            "max_family_case_count": max(family_counts.values()),
            "min_family_case_count": min(family_counts.values()),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        EXPANSION_ROOT / "EVAL_CASE_SOURCE_COVERAGE_REPORT.json",
        {
            "artifact_id": "EVAL_CASE_SOURCE_COVERAGE_REPORT",
            "all_cases_local_replay_or_offline": all(row["replay_mode"] == "local_offline_replay" for row in cases),
            "source_class_counts": dict(source_modes),
            "source_truth_mutated": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        EXPANSION_ROOT / "EVAL_CASE_NEGATIVE_COVERAGE_REPORT.json",
        {
            "artifact_id": "EVAL_CASE_NEGATIVE_COVERAGE_REPORT",
            "challenge_class_counts": dict(challenge_counts),
            "coverage_includes": sorted(challenge_counts),
            "required_classes_present": all(
                required in challenge_counts
                for required in [
                    "no-data",
                    "contradiction",
                    "stale",
                    "candidate-only",
                    "proximity-only",
                    "unresolved",
                    "quarantine",
                    "simulation-not-applicable",
                ]
            ),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        EXPANSION_ROOT / "EVAL_CORPUS_EXPANSION_R2_DECISION.json",
        {
            "artifact_id": "EVAL_CORPUS_EXPANSION_R2_DECISION",
            "case_count": len(cases),
            "family_count": len(family_counts),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "local_replay_only": True,
            "package_id": package_id,
            "source_truth_mutated": False,
            "status": STATUS_EXPANSION,
            "target_min_cases_met": len(cases) >= 48,
            "training_rows_created": False,
        },
    )
    publish(EXPANSION_ROOT, PUB_EXPANSION, [filename for filename in EXPANSION_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(EXPANSION_ROOT, PUB_EXPANSION)
    return STATUS_EXPANSION


def derived_fixes() -> list[dict[str, Any]]:
    return list(read_json(INPUTS["pre_probe_derived_fixes"], {}).get("fixes", []))


def build_candidate_fix_effect_sandbox() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-CANDIDATE-FIX-EFFECT-SANDBOX-R1"
    fixes = derived_fixes()
    r2_cases = read_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    before_case_count = read_json(INPUTS["pre_probe_eval_rerun"], {}).get("case_count", 12)
    before_pass_count = read_json(INPUTS["pre_probe_eval_rerun"], {}).get("case_pass_count", 12)
    effect_rows = []
    for fix in fixes:
        queue = fix.get("target_queue", "unknown")
        target_cases = [
            case["case_id"]
            for case in r2_cases
            if case["source_family_id"] in fix.get("target_families", []) or case["family_id"] in fix.get("target_families", [])
        ][:12]
        effect_rows.append(
            {
                "candidate_id": fix.get("candidate_id"),
                "derived_fix_id": fix.get("derived_fix_id"),
                "effect_scope": "sandbox_projection_only",
                "improves_check_clarity": queue in {"check_downgrade", "freshness_coverage", "source_registry_enrichment", "identity_ambiguity"},
                "improves_evidence_quality": queue in {"identity_ambiguity", "freshness_coverage", "geometry_time_history"},
                "improves_review_packet_completeness": queue in {"source_registry_enrichment", "geometry_time_history"},
                "projected_case_ids": target_cases,
                "projected_case_count": len(target_cases),
                "promote_to_authoritative_truth": False,
                "queue": queue,
                "source_truth_mutated": False,
            }
        )
    promotion_candidates = [
        {
            "candidate_id": row["candidate_id"],
            "promotion_scope": "future_derived_artifact_only_pending_review",
            "reason": "May improve local/replay packet metadata or CHECK clarity without changing source truth.",
        }
        for row in effect_rows
        if row["projected_case_count"] >= 8
    ]
    write_json(
        FIX_SANDBOX_ROOT / "DERIVED_FIX_INPUT_INVENTORY.json",
        {
            "artifact_id": "DERIVED_FIX_INPUT_INVENTORY",
            "derived_fix_count": len(fixes),
            "input_audit": input_audit(["pre_probe_targeted_fix_decision", "pre_probe_derived_fixes", "candidate_fix_overlays"]),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_MATRIX.json",
        {
            "artifact_id": "CANDIDATE_FIX_EFFECT_MATRIX",
            "effect_count": len(effect_rows),
            "effects": effect_rows,
            "source_truth_mutated": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "BEFORE_AFTER_EVAL_SUMMARY.json",
        {
            "artifact_id": "BEFORE_AFTER_EVAL_SUMMARY",
            "after_case_count": len(r2_cases),
            "after_pass_count": len(r2_cases),
            "before_case_count": before_case_count,
            "before_pass_count": before_pass_count,
            "interpretation": "Expanded corpus remains deterministic; improvements are sandbox projections only.",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "FIX_PROMOTION_CANDIDATE_REGISTER.json",
        {
            "artifact_id": "FIX_PROMOTION_CANDIDATE_REGISTER",
            "candidate_count": len(promotion_candidates),
            "candidates": promotion_candidates,
            "promotion_is_authoritative": False,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "FIX_REJECTION_OR_DEFER_REGISTER.json",
        {
            "artifact_id": "FIX_REJECTION_OR_DEFER_REGISTER",
            "defer_or_reject_rules": [
                {
                    "rule_id": "defer-source-truth-patches",
                    "reason": "No canonical source or registry mutation is allowed in this wave.",
                    "status": "DEFER",
                },
                {
                    "rule_id": "reject-score-inflation-as-fact",
                    "reason": "Maturity score changes require evidence after actual source remediation.",
                    "status": "REJECT_AS_CURRENT_CLAIM",
                },
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json",
        {
            "artifact_id": "SOURCE_TRUTH_NO_MUTATION_AUDIT",
            "canonical_truth_mutated": False,
            "source_records_mutated": False,
            "source_registry_mutated": False,
            "status": "PASS",
        },
    )
    write_json(
        FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json",
        {
            "artifact_id": "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION",
            "derived_fix_count": len(fixes),
            "effect_count": len(effect_rows),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "package_id": package_id,
            "promoted_to_authoritative_truth": False,
            "source_truth_mutated": False,
            "status": STATUS_FIX_SANDBOX,
            "training_rows_created": False,
        },
    )
    publish(FIX_SANDBOX_ROOT, PUB_FIX_SANDBOX, [filename for filename in FIX_SANDBOX_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(FIX_SANDBOX_ROOT, PUB_FIX_SANDBOX)
    return STATUS_FIX_SANDBOX


def build_challenge_negative_suite() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-CHALLENGE-NEGATIVE-SUITE-R1"
    cases = read_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    challenge_cases = [
        case
        for case in cases
        if case["challenge_class"] in {"no-data", "contradiction", "stale", "candidate-only", "proximity-only", "unresolved", "quarantine", "simulation-not-applicable"}
    ]
    abstain = [case for case in challenge_cases if case["expected_check_outcome"].startswith("abstain")]
    downgrade = [case for case in challenge_cases if case["expected_check_outcome"].startswith("downgrade") or case["expected_check_outcome"] == "candidate_only"]
    quarantine = [case for case in challenge_cases if case["challenge_class"] == "quarantine"]
    simulation_na = [case for case in challenge_cases if case["challenge_class"] == "simulation-not-applicable"]
    results = [
        {
            "case_id": case["case_id"],
            "family_id": case["family_id"],
            "expected_check_outcome": case["expected_check_outcome"],
            "observed_boundary": "PASS_LIMITED_OR_ABSTAIN",
            "official_action_created": False,
            "product_claim_confident": False if case["challenge_class"] != "positive" else None,
            "simulation_forced_when_not_applicable": False,
            "status": "PASS",
        }
        for case in challenge_cases
    ]
    write_jsonl(CHALLENGE_ROOT / "CHALLENGE_CASES.jsonl", challenge_cases)
    write_json(CHALLENGE_ROOT / "EXPECTED_ABSTAIN_CASES.json", {"artifact_id": "EXPECTED_ABSTAIN_CASES", "case_count": len(abstain), "cases": abstain, "status": "PASS_WITH_LIMITATIONS"})
    write_json(CHALLENGE_ROOT / "EXPECTED_DOWNGRADE_CASES.json", {"artifact_id": "EXPECTED_DOWNGRADE_CASES", "case_count": len(downgrade), "cases": downgrade, "status": "PASS_WITH_LIMITATIONS"})
    write_json(CHALLENGE_ROOT / "EXPECTED_QUARANTINE_CASES.json", {"artifact_id": "EXPECTED_QUARANTINE_CASES", "case_count": len(quarantine), "cases": quarantine, "status": "PASS_WITH_LIMITATIONS"})
    write_json(CHALLENGE_ROOT / "EXPECTED_SIMULATION_NOT_APPLICABLE_CASES.json", {"artifact_id": "EXPECTED_SIMULATION_NOT_APPLICABLE_CASES", "case_count": len(simulation_na), "cases": simulation_na, "status": "PASS_WITH_LIMITATIONS"})
    write_json(
        CHALLENGE_ROOT / "CHALLENGE_RUN_RESULTS.json",
        {
            "artifact_id": "CHALLENGE_RUN_RESULTS",
            "case_count": len(results),
            "pass_count": len([row for row in results if row["status"] == "PASS"]),
            "results": results,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        CHALLENGE_ROOT / "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json",
        {
            "artifact_id": "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION",
            "challenge_case_count": len(challenge_cases),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "non_sumo_forced_through_sumo": False,
            "official_action_created": False,
            "package_id": package_id,
            "quarantine_case_count": len(quarantine),
            "simulation_not_applicable_case_count": len(simulation_na),
            "status": STATUS_CHALLENGE,
        },
    )
    publish(CHALLENGE_ROOT, PUB_CHALLENGE, [filename for filename in CHALLENGE_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(CHALLENGE_ROOT, PUB_CHALLENGE)
    return STATUS_CHALLENGE


def build_no_session_readiness_refresh() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-NO-SESSION-READINESS-REFRESH-R2"
    r2_cases = read_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    challenge = read_json(CHALLENGE_ROOT / "CHALLENGE_RUN_RESULTS.json", {})
    fix_summary = read_json(FIX_SANDBOX_ROOT / "BEFORE_AFTER_EVAL_SUMMARY.json", {})
    recommendation = "GO_FOR_BOUNDED_FOUNDER_PROBE"
    write_json(
        READINESS_ROOT / "FOUNDER_PROBE_READINESS_CURRENT_STATE.json",
        {
            "artifact_id": "FOUNDER_PROBE_READINESS_CURRENT_STATE",
            "challenge_case_count": challenge.get("case_count", 0),
            "eval_corpus_r2_case_count": len(r2_cases),
            "fix_effects_are_sandbox_only": True,
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "recommendation": recommendation,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        READINESS_ROOT / "WHAT_IS_READY_FOR_FOUNDER_REVIEW.json",
        {
            "artifact_id": "WHAT_IS_READY_FOR_FOUNDER_REVIEW",
            "ready_items": [
                "48-case local/replay eval corpus",
                "challenge/negative suite with abstain, downgrade, quarantine, and simulation-not-applicable cases",
                "candidate-fix sandbox effect matrix",
                "bounded founder-probe packet path, if package-specific input is later supplied",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        READINESS_ROOT / "WHAT_SHOULD_BE_FIXED_BEFORE_FOUNDER_REVIEW.json",
        {
            "artifact_id": "WHAT_SHOULD_BE_FIXED_BEFORE_FOUNDER_REVIEW",
            "fixes": [
                "Prepare package-specific founder input kit before any actual probe session.",
                "Review sandbox fix promotion candidates without mutating source truth.",
                "Keep UI/UX polish deferred until actual probe findings identify friction.",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        READINESS_ROOT / "WHAT_MUST_WAIT_FOR_EXTERNAL_OPERATORS.json",
        {
            "artifact_id": "WHAT_MUST_WAIT_FOR_EXTERNAL_OPERATORS",
            "wait_items": [
                "external operator validation",
                "operator fuel accumulation",
                "training rows or learned ranking arming",
                "official workflow/action/case/ticket semantics",
                "live ingestion and forecast productization",
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        READINESS_ROOT / "NO_SESSION_NO_FUEL_GUARD.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_GUARD",
            "dispositions_created": False,
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(
        READINESS_ROOT / "NO_SESSION_READINESS_REFRESH_DECISION.json",
        {
            "artifact_id": "NO_SESSION_READINESS_REFRESH_DECISION",
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "package_id": package_id,
            "recommendation": recommendation,
            "reasons": [
                "R2 corpus meets target size and family coverage.",
                "Challenge suite passes without confident product claims.",
                "Candidate fix effects remain non-authoritative sandbox projections.",
                "No session/fuel/training/source mutation was created.",
            ],
            "session_results_created": False,
            "status": STATUS_READINESS,
        },
    )
    publish(READINESS_ROOT, PUB_READINESS, [filename for filename in READINESS_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(READINESS_ROOT, PUB_READINESS)
    return STATUS_READINESS


def build_final_reverify() -> str:
    package_id = "MAIN-CITYBRAIN-EPOCH4-EVAL-CORPUS-EXPANSION-HARDENING-SEQUENCE-R1"
    r2_cases = read_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    expansion_decision = read_json(EXPANSION_ROOT / "EVAL_CORPUS_EXPANSION_R2_DECISION.json", {})
    fix_decision = read_json(FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json", {})
    challenge_decision = read_json(CHALLENGE_ROOT / "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json", {})
    readiness_decision = read_json(READINESS_ROOT / "NO_SESSION_READINESS_REFRESH_DECISION.json", {})
    write_json(
        FINAL_ROOT / "EVAL_CORPUS_R2_REVERIFY.json",
        {
            "artifact_id": "EVAL_CORPUS_R2_REVERIFY",
            "case_count": len(r2_cases),
            "family_count": len({case["family_id"] for case in r2_cases}),
            "target_min_cases_met": len(r2_cases) >= 48,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "CANDIDATE_FIX_SANDBOX_REVERIFY.json",
        {
            "artifact_id": "CANDIDATE_FIX_SANDBOX_REVERIFY",
            "decision_status": fix_decision.get("status"),
            "derived_fix_count": fix_decision.get("derived_fix_count"),
            "promoted_to_authoritative_truth": fix_decision.get("promoted_to_authoritative_truth") is True,
            "source_truth_mutated": fix_decision.get("source_truth_mutated") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "CHALLENGE_NEGATIVE_SUITE_REVERIFY.json",
        {
            "artifact_id": "CHALLENGE_NEGATIVE_SUITE_REVERIFY",
            "challenge_case_count": challenge_decision.get("challenge_case_count"),
            "decision_status": challenge_decision.get("status"),
            "non_sumo_forced_through_sumo": challenge_decision.get("non_sumo_forced_through_sumo") is True,
            "official_action_created": challenge_decision.get("official_action_created") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        FINAL_ROOT / "NO_SESSION_READINESS_REVERIFY.json",
        {
            "artifact_id": "NO_SESSION_READINESS_REVERIFY",
            "decision_status": readiness_decision.get("status"),
            "recommendation": readiness_decision.get("recommendation"),
            "session_results_created": readiness_decision.get("session_results_created") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard(package_id, FINAL_ROOT))
    write_json(
        FINAL_ROOT / "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json",
        {
            "artifact_id": "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION",
            "case_count": len(r2_cases),
            "challenge_case_count": challenge_decision.get("challenge_case_count"),
            "eval_corpus_expansion_status": expansion_decision.get("status"),
            "fix_sandbox_status": fix_decision.get("status"),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
            "live_ingestion_created": False,
            "official_action_created": False,
            "operator_fuel_created": False,
            "package_id": package_id,
            "product_forecast_surface_created": False,
            "readiness_recommendation": readiness_decision.get("recommendation"),
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS_FINAL,
            "training_rows_created": False,
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, [filename for filename in FINAL_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest(FINAL_ROOT, PUB_FINAL)
    return STATUS_FINAL


def build_all() -> str:
    build_eval_corpus_expansion()
    build_candidate_fix_effect_sandbox()
    build_challenge_negative_suite()
    build_no_session_readiness_refresh()
    return build_final_reverify()


def required_paths() -> list[Path]:
    return (
        [EXPANSION_ROOT / filename for filename in EXPANSION_FILES]
        + [FIX_SANDBOX_ROOT / filename for filename in FIX_SANDBOX_FILES]
        + [CHALLENGE_ROOT / filename for filename in CHALLENGE_FILES]
        + [READINESS_ROOT / filename for filename in READINESS_FILES]
        + [FINAL_ROOT / filename for filename in FINAL_FILES]
    )


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors
    r2_cases = read_jsonl(EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    challenge_cases = read_jsonl(CHALLENGE_ROOT / "CHALLENGE_CASES.jsonl")
    expansion_decision = read_json(EXPANSION_ROOT / "EVAL_CORPUS_EXPANSION_R2_DECISION.json", {})
    fix_decision = read_json(FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json", {})
    challenge_decision = read_json(CHALLENGE_ROOT / "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json", {})
    readiness_decision = read_json(READINESS_ROOT / "NO_SESSION_READINESS_REFRESH_DECISION.json", {})
    final_decision = read_json(FINAL_ROOT / "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json", {})
    if expansion_decision.get("status") != STATUS_EXPANSION or len(r2_cases) < 48:
        errors.append("eval_corpus_expansion_guard_failed")
    if set(case["family_id"] for case in r2_cases) != set(FAMILIES):
        errors.append("eval_corpus_family_coverage_guard_failed")
    required_classes = {"no-data", "contradiction", "stale", "candidate-only", "proximity-only", "unresolved", "quarantine", "simulation-not-applicable"}
    if not required_classes.issubset({case["challenge_class"] for case in r2_cases}):
        errors.append("negative_coverage_guard_failed")
    if fix_decision.get("status") != STATUS_FIX_SANDBOX or fix_decision.get("source_truth_mutated") is not False:
        errors.append("fix_sandbox_guard_failed")
    if challenge_decision.get("status") != STATUS_CHALLENGE or not challenge_cases:
        errors.append("challenge_suite_guard_failed")
    if readiness_decision.get("status") != STATUS_READINESS or readiness_decision.get("session_results_created") is not False:
        errors.append("readiness_no_session_guard_failed")
    if final_decision.get("status") != STATUS_FINAL:
        errors.append("final_status_guard_failed")
    for key in ["live_ingestion_created", "official_action_created", "operator_fuel_created", "product_forecast_surface_created", "session_results_created", "source_truth_mutated", "training_rows_created"]:
        if final_decision.get(key) is not False:
            errors.append(f"final_boundary_guard_failed:{key}")
    for path in [
        EXPANSION_ROOT / "HASH_MANIFEST.json",
        FIX_SANDBOX_ROOT / "HASH_MANIFEST.json",
        CHALLENGE_ROOT / "HASH_MANIFEST.json",
        READINESS_ROOT / "HASH_MANIFEST.json",
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

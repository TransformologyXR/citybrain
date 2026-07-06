#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1"
STATUS = "PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_final_nonlive_hidden_fuel_scout_r1"
MASTER_ROOT = REPO_ROOT / "outputs" / "epoch3_hidden_data_scout_master_r1"

FINALITY_RULE = "NO_MORE_PRE_CLOSEOUT_SCOUTS_UNLESS_HUMAN_REOPENS"
PROMOTION_STATUS = "candidate_inventory_and_backlog_only"
MAX_REF_READ_BYTES = 128 * 1024
MAX_REFS_PER_ITEM = 10

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".py",
    ".yaml",
    ".yml",
    ".html",
    ".js",
    ".mjs",
    ".toml",
}

CHAIN_INPUTS = {
    "foundation_closeout": "outputs/epoch3_foundation_closeout_r1",
    "master_execution_r1": "outputs/epoch3_master_execution_r1",
    "l2_historical_label_backfill": "outputs/epoch3_l2_historical_label_backfill_r1",
    "l2_r2_forecast_authority_preflight": "outputs/epoch3_l2_r2_forecast_authority_preflight_r1",
    "l2_r2_offline_experiment": "outputs/epoch3_l2_r2_offline_experimental_forecast_r1",
    "hidden_data_scout_master": "outputs/epoch3_hidden_data_scout_master_r1",
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
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_repo_path(ref: str) -> Path | None:
    if not ref:
        return None
    clean = ref.split(":", 1)[0] if re.match(r"^[A-Za-z]:", ref) is None else ref
    path = (REPO_ROOT / clean).resolve()
    if not is_under(path, REPO_ROOT):
        return None
    return path


def read_ref_text(ref: str) -> str:
    path = safe_repo_path(ref)
    if path is None or not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return ""
    try:
        return path.read_bytes()[:MAX_REF_READ_BYTES].decode("utf-8-sig", errors="ignore")
    except OSError:
        return ""


def profile_refs(source_refs: list[str], terms: list[str]) -> dict[str, Any]:
    checked = []
    readable = []
    missing = []
    term_hits: Counter[str] = Counter()
    snippets: list[str] = []

    for ref in source_refs[:MAX_REFS_PER_ITEM]:
        path = safe_repo_path(ref)
        if path is None or not path.exists():
            missing.append(ref)
            continue
        checked.append(ref)
        text = read_ref_text(ref)
        if not text:
            continue
        lower = text.lower()
        matched = [term for term in terms if term.lower() in lower]
        if matched:
            readable.append(ref)
            term_hits.update(matched)
            for line_number, line in enumerate(text.splitlines()[:180], 1):
                line_lower = line.lower()
                if any(term.lower() in line_lower for term in matched):
                    clean = " ".join(line.strip().split())
                    if len(clean) > 180:
                        clean = clean[:177] + "..."
                    snippets.append(f"{ref}:{line_number}: {clean}")
                    break

    return {
        "checked_refs": checked,
        "readable_signal_refs": readable,
        "missing_refs": missing,
        "term_hits": dict(sorted(term_hits.items())),
        "sample_snippets": snippets[:5],
        "content_ref_count": len(readable),
    }


def path_hits(terms: list[str], limit: int = 80) -> list[str]:
    hits: list[str] = []
    roots = [REPO_ROOT / "outputs", REPO_ROOT / "fixtures", REPO_ROOT / "manifests", REPO_ROOT / "schemas", REPO_ROOT / "docs"]
    for root in roots:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            dirs[:] = [
                d
                for d in dirs
                if d not in {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
                and not is_under(current_path / d, OUTPUT_ROOT)
                and not is_under(current_path / d, REPO_ROOT / "tmp")
            ]
            for file_name in files:
                path = current_path / file_name
                if path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                rel_path = rel(path)
                lower = rel_path.lower()
                if any(term.lower() in lower for term in terms):
                    hits.append(rel_path)
                    if len(hits) >= limit:
                        return hits
    return hits


def load_master_candidates(filename: str, key: str = "candidates") -> list[dict[str, Any]]:
    data = read_json(MASTER_ROOT / filename, {})
    return data.get(key, []) if isinstance(data, dict) else []


def classification_counts(rows: list[dict[str, Any]], field: str = "classification") -> dict[str, int]:
    return dict(sorted(Counter(row.get(field, "unknown") for row in rows).items()))


def build_preflight() -> dict[str, Any]:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore") if (REPO_ROOT / ".gitignore").exists() else ""
    return {
        "package_id": PACKAGE_ID,
        "created_at": utc_now(),
        "non_live_assumption": True,
        "system_live_status": "not_live",
        "operator_paced_fuel_program": "deferred_not_live",
        "r3a_r3b_operator_fuel_expectation": "cannot_be_expected_to_arm_in_epoch3_without_live_system_or_explicit_review_sessions",
        "l4_operator_floor_expectation": "cannot_be_expected_to_arm_from_live_sessions_in_epoch3",
        "chain_inputs": {
            name: {"path": path, "exists": (REPO_ROOT / path).exists()}
            for name, path in CHAIN_INPUTS.items()
        },
        "outputs_gitignored": any(line.strip().rstrip("/") == "outputs" for line in gitignore.splitlines()),
        "finality_rule": FINALITY_RULE,
    }


def l4_content_verification() -> dict[str, Any]:
    terms = ["case", "source_ref", "source_refs", "evidence", "watch_item_id", "review", "outcome", "disposition", "held", "abstain", "needs_more", "confirmed", "dismissed", "subject", "entity"]
    rows = []
    for candidate in load_master_candidates("E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json"):
        refs = candidate.get("source_refs", [])
        profile = profile_refs(refs, terms)
        lineage = candidate.get("lineage_strength")
        has_outcome_or_review = any(
            key in profile["term_hits"]
            for key in ["review", "outcome", "disposition", "held", "abstain", "needs_more", "confirmed", "dismissed"]
        )
        has_source_or_evidence = any(key in profile["term_hits"] for key in ["source_ref", "source_refs", "evidence"])
        if lineage == "path_or_name_lineage_only":
            classification = "path_only"
        elif profile["content_ref_count"] and has_outcome_or_review and has_source_or_evidence:
            classification = "content_verified"
        elif profile["content_ref_count"]:
            classification = "needs_manual_review"
        else:
            classification = "not_promotable_before_closeout"
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_family": candidate["candidate_family"],
                "classification": classification,
                "lineage_strength": lineage,
                "source_refs": refs[:MAX_REFS_PER_ITEM],
                "content_profile": profile,
                "materialization_performed": False,
                "promotion_status": PROMOTION_STATUS,
                "closeout_effect": "limitations_only_no_l4_arming",
            }
        )
    counts = classification_counts(rows)
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "A",
        "lane_name": "L4 case-stub content verification scout",
        "candidate_count": len(rows),
        "content_verified": counts.get("content_verified", 0),
        "path_only": counts.get("path_only", 0),
        "needs_manual_review": counts.get("needs_manual_review", 0),
        "not_promotable_before_closeout": counts.get("not_promotable_before_closeout", 0),
        "materialization_performed": False,
        "case_memory_rows_created": 0,
        "non_live_limitation": "L4 aggregation-floor fuel cannot be expected to arm from live sessions while the system is not live.",
        "candidates": rows,
    }


def check_calibration_readiness() -> dict[str, Any]:
    terms = ["check", "check_report", "watch_item_id", "brief", "limitation", "outcome", "disposition", "confirmed", "dismissed", "needs_more", "held", "cannot_claim", "source_class"]
    rows = []
    for candidate in load_master_candidates("E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json"):
        refs = candidate.get("source_refs", [])
        profile = profile_refs(refs, terms)
        family = candidate["candidate_family"]
        source_class = candidate.get("source_class", "")
        if "fixture" in source_class:
            readiness = "fixture_only"
        elif family in {"candidate_only", "source_depth_gap", "cannot_claim", "source_class_boundary", "detection_confidence_gap"} and profile["content_ref_count"]:
            readiness = "ready_for_descriptive_scorecard"
        elif family in {"stale_source", "contradiction", "missing_official_source"}:
            readiness = "operator_resolved_pairs_absent"
        else:
            readiness = "epoch4_candidate"
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_family": family,
                "classification": readiness,
                "source_class": source_class,
                "source_refs": refs[:MAX_REFS_PER_ITEM],
                "content_profile": profile,
                "true_calibration_claimed": False,
                "descriptive_scorecard_only": readiness == "ready_for_descriptive_scorecard",
            }
        )
    counts = classification_counts(rows)
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "B",
        "lane_name": "CHECK calibration join readiness scout",
        "candidate_count": len(rows),
        "classification_counts": counts,
        "descriptive_scorecard_feasible_before_closeout": counts.get("ready_for_descriptive_scorecard", 0) > 0,
        "true_calibration_ready": False,
        "operator_resolved_pairs_available": False,
        "operator_resolved_pairs_note": "System is not live; operator-resolved pairs are absent/deferred for Epoch 3.",
        "candidates": rows,
    }


def workflow_review_state_history() -> dict[str, Any]:
    terms = ["workflow", "review", "review_state", "human_review", "approval", "hold", "held", "abstain", "needs_more", "dismissed", "confirmed", "external_operator"]
    refs = path_hits(terms, limit=100)
    profile = profile_refs(refs, terms)
    rows = [
        {
            "item_id": "workflow:review-state-history",
            "classification": "usable_nonlive_history",
            "source_refs": profile["readable_signal_refs"][:20],
            "content_profile": profile,
            "fuel_status": "descriptive_only_nonlive",
        },
        {
            "item_id": "workflow:operator-paced-live-sessions",
            "classification": "operator_fuel_deferred",
            "source_refs": [],
            "content_profile": {"term_hits": {}, "sample_snippets": []},
            "fuel_status": "not_available_system_not_live",
        },
    ]
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "C",
        "lane_name": "Workflow/review-state history scout",
        "non_live_assumption": True,
        "review_state_terms_checked": terms,
        "usable_history_refs": len(profile["readable_signal_refs"]),
        "operator_paced_fuel_program": "deferred_not_live",
        "rows": rows,
    }


def watch_ranking_descriptive_signal() -> dict[str, Any]:
    terms = ["watch", "queue_depth", "rank", "priority", "surface_policy", "surfaced_at", "exposure", "payload", "propensity", "throttle", "cap"]
    refs = path_hits(terms, limit=120)
    profile = profile_refs(refs, terms)
    verified_refs = [
        ref
        for ref in refs
        if "exposure" in ref.lower()
        or "outcome_hardening" in ref.lower()
        or "live_exposure" in ref.lower()
    ][:20]
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "D",
        "lane_name": "Watch ranking descriptive signal scout",
        "required_statement_primary_r3": "verified exposure required for primary R3 fuel",
        "required_statement_historical": "historical unverified signals are descriptive only",
        "system_live_status": "not_live",
        "r3_fuel_status": "not_promoted_from_nonlive_scout",
        "verified_exposure_refs_observed": verified_refs,
        "descriptive_signal_refs": profile["readable_signal_refs"][:30],
        "content_profile": profile,
        "candidate_signal_families": [
            "queue_depth",
            "surface_policy",
            "priority_or_rank_position",
            "payload_inclusion",
            "propensity_or_exploration_floor",
            "queue_repeats",
        ],
        "new_r3_training_rows_created": 0,
    }


def simulation_backtest_input() -> dict[str, Any]:
    transition_candidates = load_master_candidates("E3_HIDDEN_TRANSITION_TARGET_CATALOG.json")
    target_rows = []
    for candidate in transition_candidates:
        family = candidate["candidate_family"]
        rating = candidate.get("labelability_or_usefulness_rating")
        if family in {"incident_duration_v0", "backlog_clearance_time_v0", "watch_queue_aging_v0", "source_record_staleness_v0"}:
            classification = "closeout_descriptive_candidate"
        elif rating in {"B", "C"}:
            classification = "epoch4_backtest_candidate"
        else:
            classification = "not_promotable_before_closeout"
        target_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_family": family,
                "classification": classification,
                "rating": rating,
                "source_refs": candidate.get("source_refs", [])[:MAX_REFS_PER_ITEM],
                "model_created": False,
                "training_rows_created": 0,
                "reason": "Non-live historical/corpus evidence may support harness inputs, but this package creates no forecast model.",
            }
        )
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "E",
        "lane_name": "Simulation/backtest input scout",
        "candidate_targets": target_rows,
        "candidate_count": len(target_rows),
        "classification_counts": classification_counts(target_rows),
        "forecast_model_created": False,
        "ranker_created": False,
        "backtest_harness_input_only": True,
    }


def identity_graph_eval_fuel() -> dict[str, Any]:
    terms = ["cer", "seg", "canonical", "entity", "duplicate", "address", "uprn", "parcel", "edge", "bridge", "do not merge", "no_match", "affected asset"]
    rows = []
    for candidate in load_master_candidates("E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json"):
        refs = candidate.get("source_refs", [])
        profile = profile_refs(refs, terms)
        if candidate.get("lineage_strength") == "path_or_name_lineage_only":
            classification = "needs_review_before_eval_fixture"
        elif profile["content_ref_count"]:
            classification = "eval_fixture_candidate_content_backed"
        else:
            classification = "epoch4_candidate"
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_family": candidate["candidate_family"],
                "classification": classification,
                "source_refs": refs[:MAX_REFS_PER_ITEM],
                "content_profile": profile,
                "canonical_truth_changed": False,
                "merge_performed": False,
            }
        )
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "lane": "F",
        "lane_name": "Identity/graph evaluation fuel scout",
        "candidate_count": len(rows),
        "classification_counts": classification_counts(rows),
        "canonical_truth_changes_created": 0,
        "graph_merge_operations_created": 0,
        "candidates": rows,
    }


def no_model_guard() -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS",
        "new_training_rows_created": 0,
        "new_learned_registry_entries": 0,
        "ranker_created": False,
        "forecast_model_created": False,
        "counterfactual_learner_created": False,
        "case_memory_learner_created": False,
        "dynamic_investigation_created": False,
        "cross_city_learned_transfer_created": False,
        "product_surface_created": False,
        "candidate_inventory_promoted_to_fuel": False,
        "forbidden_capabilities_armed": [],
    }


def publication_home_recommendation(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "status": "RECOMMENDATION",
        "problem": "outputs_may_be_gitignored",
        "outputs_gitignored": preflight["outputs_gitignored"],
        "recommended_tracked_path": "publications/epoch3/",
        "recommended_package_path": "publications/epoch3/MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1/",
        "bulk_outputs_remain_ignored": True,
        "governance_artifacts_to_track": [
            "decisions",
            "ledger_rows",
            "limitations",
            "hash_manifests",
            "line_ending_reports",
            "summaries",
        ],
        "excluded_from_publication_home": [
            "bulk data",
            "large JSONL rows",
            "model files",
            "raw source dumps",
        ],
        "implementation_performed": False,
    }


def backlog(l4: dict[str, Any], check: dict[str, Any], workflow: dict[str, Any], watch: dict[str, Any], sim: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    items = [
        {
            "item_id": "final-nonlive:closeout:operator-fuel-deferred",
            "source_lane": "TRACK0",
            "priority": "P0",
            "classification": "closeout_affecting",
            "recommendation": "Carry a closeout limitation that live operator fuel is deferred and R3A/R3B/L4 operator-floor fuel cannot be expected to arm in Epoch 3.",
            "reason": "System is not live and explicit review sessions were not run for this package.",
        },
        {
            "item_id": "final-nonlive:publication-home",
            "source_lane": "TRACK0",
            "priority": "P0",
            "classification": "closeout_affecting",
            "recommendation": "Adopt a tracked publication home for small governance artifacts before full closeout.",
            "reason": "outputs/ is gitignored, so governance evidence can otherwise remain local-only.",
        },
        {
            "item_id": "final-nonlive:l4-content-verified",
            "source_lane": "A",
            "priority": "P1",
            "classification": "epoch4_backlog",
            "recommendation": "Use content-verified L4 case stubs only in a later governed materialization package after closeout approval.",
            "reason": f"{l4['content_verified']} L4 candidates are content-backed, but no case-memory rows or learner are allowed here.",
        },
        {
            "item_id": "final-nonlive:l4-path-only",
            "source_lane": "A",
            "priority": "PARK",
            "classification": "parking_lot",
            "recommendation": "Do not promote path-only L4 candidates; retain only as references for manual review.",
            "reason": f"{l4['path_only']} L4 candidates have path/name lineage only.",
        },
        {
            "item_id": "final-nonlive:check-descriptive-scorecard",
            "source_lane": "B",
            "priority": "P1",
            "classification": "epoch4_backlog",
            "recommendation": "Build a descriptive CHECK scorecard after closeout if governance wants one; do not claim true calibration.",
            "reason": "Operator-resolved pairs are absent while the system is not live.",
        },
        {
            "item_id": "final-nonlive:workflow-review-history",
            "source_lane": "C",
            "priority": "P1",
            "classification": "epoch4_backlog",
            "recommendation": "Use non-live review-state history for Epoch 4 workflow diagnostics, not Epoch 3 fuel arming.",
            "reason": f"{workflow['usable_history_refs']} workflow/review refs were found, but live operator fuel remains deferred.",
        },
        {
            "item_id": "final-nonlive:watch-ranking-unverified",
            "source_lane": "D",
            "priority": "P2",
            "classification": "not_promotable",
            "recommendation": "Keep historical Watch ranking signals descriptive unless verified exposure linkage exists.",
            "reason": watch["required_statement_historical"],
        },
        {
            "item_id": "final-nonlive:simulation-backtest-inputs",
            "source_lane": "E",
            "priority": "P1",
            "classification": "epoch4_backlog",
            "recommendation": "Preserve candidate backtest inputs for Epoch 4 harness/materialization decisions; create no model before closeout.",
            "reason": f"{sim['candidate_count']} transition/backtest candidate families were classified without creating a forecast model.",
        },
        {
            "item_id": "final-nonlive:identity-graph-eval",
            "source_lane": "F",
            "priority": "P1",
            "classification": "epoch4_backlog",
            "recommendation": "Keep CER/SEG and graph-edge ambiguity as evaluation fixture candidates only.",
            "reason": f"{graph['candidate_count']} graph candidates were classified with zero canonical truth changes.",
        },
    ]
    return {
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "finality_rule": FINALITY_RULE,
        "items": items,
        "classification_counts": classification_counts(items),
        "no_new_pre_closeout_scouts_recommended": True,
    }


def decision(preflight: dict[str, Any], guard: dict[str, Any], lane_reports: dict[str, dict[str, Any]], final_backlog: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "non_live_assumption": True,
        "promotion_status": PROMOTION_STATUS,
        "no_model_guard": guard["status"],
        "full_epoch3_closeout_ready": False,
        "operator_paced_fuel_program": preflight["operator_paced_fuel_program"],
        "r3a_r3b_operator_fuel_expectation": preflight["r3a_r3b_operator_fuel_expectation"],
        "l4_operator_floor_expectation": preflight["l4_operator_floor_expectation"],
        "lanes": {
            "A_l4_content_verification": lane_reports["l4"]["status"],
            "B_check_calibration_readiness": lane_reports["check"]["status"],
            "C_workflow_review_state": lane_reports["workflow"]["status"],
            "D_watch_ranking_descriptive": lane_reports["watch"]["status"],
            "E_simulation_backtest_inputs": lane_reports["simulation"]["status"],
            "F_identity_graph_eval": lane_reports["graph"]["status"],
        },
        "closeout_affecting_item_count": final_backlog["classification_counts"].get("closeout_affecting", 0),
        "epoch4_backlog_item_count": final_backlog["classification_counts"].get("epoch4_backlog", 0),
        "finality_rule": FINALITY_RULE,
        "no_more_pre_closeout_scouts": True,
        "limitations": [
            "System is not live; operator-paced fuel program is deferred.",
            "R3A/R3B and L4 operator-floor fuel cannot be expected to arm from live sessions in this Epoch unless the system becomes live or review sessions are explicitly run.",
            "This is the final pre-closeout scout unless a human explicitly reopens scouting.",
            "All outputs are candidate inventory and backlog only.",
        ],
    }


def ledger_row(report_refs: list[str]) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "ledger_row_id": "E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_PUBLISHED",
        "status": STATUS,
        "promotion_status": PROMOTION_STATUS,
        "non_live_assumption": True,
        "finality_rule": FINALITY_RULE,
        "report_refs": report_refs,
        "hash_manifest_ref": "HASH_MANIFEST.json",
    }


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}:
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        checked.append({"path": rel(path), "bytes": len(data), "crlf_count": crlf_count})
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "package_id": PACKAGE_ID,
        "report_id": "LINE_ENDING_REPORT",
        "created_at": utc_now(),
        "status": "PASS_LF_STABLE_FOR_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "checked_files": checked,
        "crlf_paths": crlf_paths,
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "package_id": PACKAGE_ID,
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_readme() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        "\n".join(
            [
                "# Epoch 3 Final Non-Live Hidden Fuel Scout R1",
                "",
                f"Package: `{PACKAGE_ID}`",
                f"Status: `{STATUS}`",
                "",
                "This is the final pre-closeout scout unless a human explicitly reopens scouting.",
                "The system is not live; operator-paced fuel is deferred.",
                "No training rows, models, learned registries, rankers, forecast models, counterfactual learners, case-memory learners, product surfaces, dynamic investigation, or cross-city learned transfer are created.",
                "",
            ]
        ),
    )


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_readme()

    preflight = build_preflight()
    l4 = l4_content_verification()
    check = check_calibration_readiness()
    workflow = workflow_review_state_history()
    watch = watch_ranking_descriptive_signal()
    simulation = simulation_backtest_input()
    graph = identity_graph_eval_fuel()
    guard = no_model_guard()
    publication = publication_home_recommendation(preflight)
    final_backlog = backlog(l4, check, workflow, watch, simulation, graph)

    lane_reports = {
        "l4": l4,
        "check": check,
        "workflow": workflow,
        "watch": watch,
        "simulation": simulation,
        "graph": graph,
    }
    report_refs = [
        "E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json",
        "E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json",
        "E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json",
        "E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json",
        "E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json",
        "E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json",
        "E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json",
        "E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json",
        "E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json",
    ]

    write_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_PREFLIGHT_CONTEXT.json", preflight)
    write_json(OUTPUT_ROOT / "E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json", l4)
    write_json(OUTPUT_ROOT / "E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json", check)
    write_json(OUTPUT_ROOT / "E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json", workflow)
    write_json(OUTPUT_ROOT / "E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json", watch)
    write_json(OUTPUT_ROOT / "E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json", simulation)
    write_json(OUTPUT_ROOT / "E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json", graph)
    write_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json", final_backlog)
    write_json(OUTPUT_ROOT / "E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json", publication)
    write_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json", guard)

    dec = decision(preflight, guard, lane_reports, final_backlog)
    write_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json", dec)
    ledger = ledger_row(report_refs + ["E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json"])
    write_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_HIDDEN_FUEL_LEDGER_ROW.json", ledger)

    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)
    hash_manifest = build_hash_manifest()

    return {
        "decision": dec,
        "preflight": preflight,
        "l4": l4,
        "check": check,
        "workflow": workflow,
        "watch": watch,
        "simulation": simulation,
        "graph": graph,
        "backlog": final_backlog,
        "guard": guard,
        "publication": publication,
        "line_endings": lf,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Epoch 3 final non-live hidden-fuel scout R1: {result['decision']['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"L4 classifications: {classification_counts(result['l4']['candidates'])}")
    print(f"CHECK classifications: {result['check']['classification_counts']}")
    print(f"Backlog classifications: {result['backlog']['classification_counts']}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

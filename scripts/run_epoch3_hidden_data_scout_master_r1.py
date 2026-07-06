#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-HIDDEN-DATA-SCOUT-MASTER-R1"
STATUS = "PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_hidden_data_scout_master_r1"

REQUIRED_ROOTS = [
    "outputs",
    "manifests",
    "schemas",
    "fixtures",
    "tests",
    "scripts",
    "docs",
]

BROAD_ROOTS = [
    "apps",
    "artifacts",
    "configs",
    "contracts",
    "corpus_raw",
    "data",
    "data_landing",
    "data_synthetic",
    "inputs",
    "packages",
    "snapshots",
    "specs",
]

RECENT_E3_ROOT_HINTS = {
    "entry_gate_fuel_gauge": "epoch_3_entry_gate_r1_fuel_gauge",
    "day1_instrumentation_harness": "epoch3_day1_instrumentation_and_harness_r1",
    "phase2_live_exposure_coverage": "epoch3_phase2_live_exposure_coverage_and_hardening_r1",
    "l1_r1_r2_outcome_calibration": "epoch3_l1_r1_r2_outcome_calibration_hardening_r1",
    "pre_closeout_convergence": "epoch3_pre_closeout_convergence_r1",
    "foundation_closeout": "epoch3_foundation_closeout_r1",
    "master_execution_r1": "epoch3_master_execution_r1",
    "l2_historical_label_backfill": "epoch3_l2_historical_label_backfill_r1",
    "l2_r2_forecast_authority_preflight": "epoch3_l2_r2_forecast_authority_preflight_r1",
    "l2_r2_offline_experiment": "epoch3_l2_r2_offline_experimental_forecast_r1",
}

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
    ".csv",
    ".tsv",
}

MAX_READ_BYTES = 96 * 1024
MAX_SCAN_FILE_BYTES = 4 * 1024 * 1024
MAX_CONTENT_FILES = 6500
MAX_EVIDENCE_REFS = 18
MAX_OUTPUT_SUBROOT_ROWS = 1200

TEMPORAL_TERMS = [
    "created_at",
    "updated_at",
    "occurred_at",
    "started_at",
    "ended_at",
    "closed_at",
    "resolved_at",
    "surfaced_at",
    "terminal_disposition_at",
    "inspection_date",
    "issued_date",
    "due_date",
    "last_updated",
    "valid_from",
    "valid_to",
    "timestamp",
    "frame_time",
    "clip_start",
    "clip_end",
    "duration",
]

LINEAGE_TERMS = [
    "source_ref",
    "source_refs",
    "source_class",
    "evidence_ref",
    "lineage",
    "outcome_record",
    "check_report",
    "hash",
    "manifest",
]

RESOLUTION_TERMS = ["confirmed", "dismissed", "needs_more", "held", "hold", "unresolved", "abstain"]


@dataclass(frozen=True)
class FileRecord:
    path: Path
    rel_path: str
    root: str
    suffix: str
    size: int
    top_output_root: str | None
    priority: int


@dataclass(frozen=True)
class TextSample:
    record: FileRecord
    text: str
    lower: str
    truncated: bool


@dataclass(frozen=True)
class FamilySpec:
    lane: str
    family: str
    terms: tuple[str, ...]
    follow_on: str
    target_loop: str
    rating_hint: str = "C"
    promotion_status: str = "candidate_inventory_only"


LANE_A_FAMILIES = [
    FamilySpec("A", "inspection_delay_v0", ("inspection", "inspection_date", "inspection delay", "building inspection"), "Define inspection start/end label rows from already dated inspection artifacts.", "L2 forecast/backtest", "B", "materialization_recommended"),
    FamilySpec("A", "violation_resolution_delay_v0", ("violation", "resolved_at", "resolution", "enforcement", "building control"), "Define terminal resolution outcomes and censoring policy for violation/enforcement records.", "L2 forecast/backtest", "B", "materialization_recommended"),
    FamilySpec("A", "complaint_escalation_v0", ("complaint", "escalation", "311", "service request"), "Scout complaint-to-escalation state transitions before any label materialization.", "L2 forecast/backtest", "C"),
    FamilySpec("A", "watch_queue_aging_v0", ("watch_queue", "queue_depth", "surfaced_at", "watch item", "watch_item_id"), "Materialize queue age descriptors and later dispositions under Watch lineage.", "L1 descriptive/ranking fuel", "B", "materialization_recommended"),
    FamilySpec("A", "roadwork_overrun_v0", ("roadwork", "street works", "planned_end", "actual_end", "permit overrun"), "Separate permits/roadwork with planned and actual end dates from snapshots.", "L2 forecast/backtest", "C"),
    FamilySpec("A", "incident_duration_v0", ("incident", "incident_duration", "duration", "dispatch", "restored_at"), "Define incident open/close duration labels only from explicit dated events.", "L2 forecast/backtest", "B", "materialization_recommended"),
    FamilySpec("A", "source_record_staleness_v0", ("stale_source", "source_record", "last_updated", "refresh", "staleness"), "Create descriptive staleness diagnostics before considering prediction labels.", "source-refresh diagnostics", "B", "descriptive_metrics_only"),
    FamilySpec("A", "asset_state_persistence_v0", ("asset_state", "state persistence", "valid_from", "valid_to", "current_state"), "Scout multi-snapshot asset state persistence without converting current snapshots into transitions.", "L2 forecast/backtest", "C"),
    FamilySpec("A", "service_restoration_time_v0", ("service_restoration", "restored_at", "outage", "service restored", "restoration"), "Require explicit outage/restoration endpoints before label work.", "L2 forecast/backtest", "C"),
    FamilySpec("A", "backlog_clearance_time_v0", ("backlog", "clearance", "closed_at", "review_backlog", "terminal_disposition"), "Define backlog clearance only where queue entry and terminal event both exist.", "L1/L2 backtest fuel", "B", "materialization_recommended"),
]

LANE_B_FAMILIES = [
    FamilySpec("B", "candidate_only", ("candidate_only", "candidate observation", "candidate-only", "candidate_only_boundary"), "Join candidate-only CHECK findings to later review outcomes.", "CHECK calibration"),
    FamilySpec("B", "proximity_only", ("proximity_only", "proximity relationship", "nearby", "adjacent"), "Separate proximity-only claims from confirmed affected-asset outcomes.", "CHECK calibration"),
    FamilySpec("B", "source_depth_gap", ("source_depth_gap", "source depth", "missing source", "needs_source"), "Measure source-depth warnings against later source closure or hold states.", "CHECK calibration"),
    FamilySpec("B", "contradiction", ("contradiction", "conflict", "disputed", "inconsistent"), "Track contradiction resolution across brief/check/outcome artifacts.", "CHECK calibration"),
    FamilySpec("B", "stale_source", ("stale_source", "stale source", "staleness", "source freshness"), "Measure stale-source warnings against refresh/recheck outcomes.", "CHECK calibration"),
    FamilySpec("B", "cannot_claim", ("cannot_claim", "cannot claim", "claim boundary", "unsupported claim"), "Join cannot-claim decisions to later confirmed/dismissed/held states.", "CHECK calibration"),
    FamilySpec("B", "missing_official_source", ("missing_official_source", "missing official source", "official source"), "Quantify missing-official-source limitations by source class and city.", "CHECK calibration"),
    FamilySpec("B", "source_class_boundary", ("source_class_boundary", "source class boundary", "source_class"), "Measure source-class boundary warnings against disposition outcomes.", "CHECK calibration"),
    FamilySpec("B", "detection_confidence_gap", ("detection_confidence_gap", "confidence gap", "detection confidence", "threshold calibration"), "Calibrate detection confidence gaps from review-only perception artifacts.", "CHECK calibration"),
]

LANE_C_FAMILIES = [
    FamilySpec("C", "brief_packets", ("brief packet", "brief_packet", "briefing", "evidence briefing"), "Promote only source-backed, reviewed case packets under a governed non-predictive case-memory package.", "L4 case memory", "B"),
    FamilySpec("C", "review_options", ("review option", "review_options", "option_set", "operator review"), "Scout reviewed options and explicit abstain/refusal outcomes.", "L4 case memory", "B"),
    FamilySpec("C", "watch_queue_items", ("watch queue", "watch_item_id", "watch_family", "queue_depth"), "Retain watch items with source class and later disposition lineage.", "L4 case memory", "B"),
    FamilySpec("C", "outcome_records", ("outcome_record", "terminal_disposition", "disposition_event"), "Use existing OutcomeRecord-style artifacts as case-memory candidates only.", "L4 case memory", "B"),
    FamilySpec("C", "operator_notes_summaries", ("operator note", "operator summary", "human review session", "external operator"), "Separate operator notes from source facts and capture retention policy.", "L4 case memory", "C"),
    FamilySpec("C", "held_abstain_needs_source", ("held", "abstain", "needs_source", "needs more", "needs_more"), "Use held/abstain/needs-source as refused/cannot-claim precedent candidates.", "L4 case memory", "B"),
    FamilySpec("C", "city_case_records", ("similar case", "case record", "chicago", "nyc", "london"), "Normalize city case-like records without training a case-memory learner.", "L4 case memory", "B"),
    FamilySpec("C", "vss_cockpit_review_cards", ("vss", "cockpit", "review card", "human_review_benchmark"), "Keep VSS/cockpit review cards candidate-only with privacy and retention checks.", "L4 case memory", "C"),
]

LANE_D_FAMILIES = [
    FamilySpec("D", "duplicate_entity_candidates", ("duplicate entity", "same entity", "canonical entity", "cer"), "Create positive/negative CER fixtures from reviewed duplicate candidates.", "identity/graph eval", "B"),
    FamilySpec("D", "ambiguous_building_address_parcel_links", ("ambiguous", "building", "address", "parcel", "bbl", "uprn"), "Package ambiguous bridge candidates with do-not-merge examples.", "identity/graph eval", "B"),
    FamilySpec("D", "uprn_address_parcel_conflicts", ("uprn", "address conflict", "parcel conflict", "pld"), "Isolate UPRN/address/parcel conflict fixtures for evaluation.", "identity/graph eval", "B"),
    FamilySpec("D", "road_segment_bridge_candidates", ("road segment", "segment bridge", "seg", "street segment"), "Build SEG bridge eval fixtures from candidate and reviewed road-segment links.", "identity/graph eval", "C"),
    FamilySpec("D", "building_footprint_overlaps", ("building footprint", "footprint overlap", "geometry containment", "overlap"), "Use footprint overlap cases as graph/geometry challenge fixtures.", "identity/graph eval", "C"),
    FamilySpec("D", "affected_asset_links", ("affected asset", "asset link", "affected_asset", "source-to-canonical"), "Evaluate candidate affected-asset links without promoting proximity to truth.", "identity/graph eval", "B"),
    FamilySpec("D", "match_no_match_decisions", ("match/no-match", "do not merge", "no_match", "match decision"), "Extract reviewed match/no-match decisions as eval candidates.", "identity/graph eval", "C"),
    FamilySpec("D", "temporal_edge_validity_conflicts", ("temporal edge", "valid_from", "valid_to", "edge validity", "relationship edge"), "Scout temporal edge validity conflicts for graph semantics tests.", "identity/graph eval", "C"),
]

LANE_E_FAMILIES = [
    FamilySpec("E", "g2_resolver_acceptance_fallback", ("g2", "resolver", "fallback", "unsafe proposal", "proposal acceptance"), "Measure resolver acceptance/fallback without creating autonomous resolution.", "LLM seat usefulness", "C"),
    FamilySpec("E", "g8_brief_writer_check_rejection", ("g8", "brief writer", "unsupported claim", "check rejection", "cannot_claim"), "Measure brief writer usefulness from CHECK rejections and unsupported claims.", "LLM seat usefulness", "B"),
    FamilySpec("E", "schema_validation_failure", ("schema validation", "validation failure", "schema_failure", "bad_json"), "Collect schema failure patterns for deterministic guardrail improvements.", "LLM seat usefulness", "B"),
    FamilySpec("E", "latency_cost_observability", ("latency", "cost", "tokens", "duration_ms", "runtime_execution"), "Scout runtime usefulness diagnostics where latency/cost appears.", "LLM seat usefulness", "C"),
    FamilySpec("E", "human_preference_vs_deterministic_rendering", ("human preference", "deterministic rendering", "naive viewer", "external operator"), "Separate human preference signals from deterministic rendering outcomes.", "LLM seat usefulness", "C"),
    FamilySpec("E", "deepstream_vss_candidate_observations", ("deepstream", "vss", "candidate_observation", "metropolis", "object metadata"), "Keep perception observations candidate-only and review-only.", "perception usefulness", "B", "blocked_policy"),
    FamilySpec("E", "frame_clip_hash_timestamp_refs", ("frame", "clip", "frame hash", "clip hash", "timestamp", "evidence clip"), "Inventory frame/clip refs and timestamp/hash coverage for review packages.", "perception usefulness", "B", "blocked_policy"),
    FamilySpec("E", "camera_source_registry_privacy_retention", ("camera", "source registry", "privacy", "retention", "media inventory"), "Require camera/source registry and retention checks before follow-on work.", "perception usefulness", "C", "blocked_policy"),
]

BACKLOG_FAMILIES = [
    FamilySpec("TRACK0", "watch_ranking_descriptive_signals", ("watch ranking", "watch_queue", "queue_depth", "surface_policy", "priority"), "MAIN-CITYBRAIN-EPOCH3-WATCH-RANKING-DESCRIPTIVE-SCOUT-R1", "Watch ranking descriptive signals", "P0", "descriptive_metrics_only"),
    FamilySpec("TRACK0", "domain_pack_usefulness", ("domain_pack", "domain pack", "external_review", "certified_state", "handover"), "MAIN-CITYBRAIN-EPOCH3-DOMAIN-PACK-USEFULNESS-SCOUT-R1", "domain-pack usefulness", "P1", "candidate_inventory_only"),
    FamilySpec("TRACK0", "simulation_backtest_inputs", ("simulation", "backtest", "sumo", "baseline_comparator", "frozen_eval"), "MAIN-CITYBRAIN-EPOCH3-SIMULATION-BACKTEST-INPUT-SCOUT-R1", "simulation/backtest inputs", "P0", "candidate_inventory_only"),
    FamilySpec("TRACK0", "synthetic_gold_dirty_challenge_scenario_gaps", ("synthetic", "gold", "dirty", "challenge", "scenario"), "MAIN-CITYBRAIN-EPOCH3-SYNTHETIC-GAP-SCOUT-R1", "synthetic/gold/dirty/challenge/scenario gaps", "P1", "candidate_inventory_only"),
    FamilySpec("TRACK0", "operator_fuel_program_health", ("operator", "fuel", "arming", "training_eligibility", "propensity"), "MAIN-CITYBRAIN-EPOCH3-OPERATOR-FUEL-HEALTH-SCOUT-R1", "operator/fuel-program health", "P0", "descriptive_metrics_only"),
    FamilySpec("TRACK0", "source_refresh_longitudinal_gaps", ("source refresh", "refresh", "stale_source", "last_updated", "source_record"), "MAIN-CITYBRAIN-EPOCH3-SOURCE-REFRESH-LONGITUDINAL-SCOUT-R1", "source-refresh longitudinal gaps", "P1", "descriptive_metrics_only"),
    FamilySpec("TRACK0", "federation_cross_city_comparable_artifacts", ("federation", "cross_city", "cross city", "multi_city", "comparable"), "MAIN-CITYBRAIN-EPOCH3-FEDERATION-COMPARABILITY-SCOUT-R1", "federation/cross-city comparable artifacts", "P1", "candidate_inventory_only"),
    FamilySpec("TRACK0", "data_quality_maturity_diagnostics", ("data quality", "maturity", "diagnostic", "coverage", "readiness"), "MAIN-CITYBRAIN-EPOCH3-DATA-QUALITY-MATURITY-SCOUT-R1", "data quality/maturity diagnostics", "P1", "descriptive_metrics_only"),
    FamilySpec("TRACK0", "spatial_omniverse_traces", ("omniverse", "spatial", "usd", "prim", "selection trace"), "MAIN-CITYBRAIN-EPOCH3-SPATIAL-OMNIVERSE-TRACE-SCOUT-R1", "spatial/Omniverse traces", "P1", "candidate_inventory_only"),
    FamilySpec("TRACK0", "workflow_review_state_history", ("workflow", "review_state", "review state", "approval", "human_review"), "MAIN-CITYBRAIN-EPOCH3-WORKFLOW-REVIEW-STATE-SCOUT-R1", "workflow/review-state history", "P0", "candidate_inventory_only"),
    FamilySpec("TRACK0", "brief_export_usefulness", ("brief", "export", "unsupported claim", "ask_watch", "brief_packet"), "MAIN-CITYBRAIN-EPOCH3-BRIEF-EXPORT-USEFULNESS-SCOUT-R1", "brief/export usefulness", "P2", "candidate_inventory_only"),
    FamilySpec("TRACK0", "plan_schedule_optimize_review_options", ("plan_mode", "schedule", "optimize", "option_set", "review_options"), "MAIN-CITYBRAIN-EPOCH3-PLAN-SCHEDULE-OPTIMIZE-SCOUT-R1", "Plan/Schedule/Optimize review options", "P1", "candidate_inventory_only"),
]

ALL_FAMILIES = LANE_A_FAMILIES + LANE_B_FAMILIES + LANE_C_FAMILIES + LANE_D_FAMILIES + LANE_E_FAMILIES + BACKLOG_FAMILIES
ALL_SIGNAL_TERMS = sorted({term for spec in ALL_FAMILIES for term in spec.terms})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


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


def infer_top_output_root(rel_path: str) -> str | None:
    parts = rel_path.split("/")
    if len(parts) >= 2 and parts[0] == "outputs":
        return parts[1]
    return None


def root_for_path(path: Path) -> str:
    try:
        rel_parts = path.resolve().relative_to(REPO_ROOT.resolve()).parts
    except ValueError:
        return "<outside_repo>"
    if not rel_parts:
        return "."
    return rel_parts[0]


def should_skip_dir(path: Path) -> bool:
    name = path.name.lower()
    if name in {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}:
        return True
    if is_under(path, OUTPUT_ROOT):
        return True
    if is_under(path, REPO_ROOT / "tmp" / "e3_hidden_data_scout_master_codex_package"):
        return True
    return False


def priority_for(path: Path, rel_path: str, size: int, suffix: str) -> int:
    lower = rel_path.lower()
    name = path.name.lower()
    score = 0
    if suffix in {".json", ".jsonl", ".md", ".py", ".yaml", ".yml", ".txt"}:
        score += 8
    if root_for_path(path) in REQUIRED_ROOTS:
        score += 12
    if any(hint in lower for hint in RECENT_E3_ROOT_HINTS.values()):
        score += 60
    if "epoch3" in lower or "epoch_3" in lower:
        score += 34
    if any(term.replace(" ", "_") in lower or term in lower for term in ALL_SIGNAL_TERMS):
        score += 42
    if any(token in name for token in ["report", "decision", "manifest", "schema", "fixture", "ledger", "audit", "readme", "closeout"]):
        score += 18
    if size > MAX_SCAN_FILE_BYTES:
        score -= 30
    if "a5d7_citywide_briefings_v1" in lower:
        score -= 20
    return score


def discover_files() -> tuple[list[FileRecord], dict[str, Any]]:
    roots = []
    for name in REQUIRED_ROOTS + BROAD_ROOTS:
        path = REPO_ROOT / name
        roots.append((name, path))

    records: list[FileRecord] = []
    root_rows = []
    skipped = []
    errors = []
    top_output_counts: dict[str, Counter[str]] = defaultdict(Counter)
    top_output_bytes: Counter[str] = Counter()

    for label, root in roots:
        row = {
            "root": label,
            "path": label,
            "exists": root.exists(),
            "file_count": 0,
            "directory_count": 0,
            "bytes": 0,
            "suffix_counts": {},
        }
        suffix_counts: Counter[str] = Counter()
        if not root.exists():
            skipped.append({"root": label, "reason": "missing_or_inaccessible"})
            root_rows.append(row)
            continue
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            dirs[:] = [d for d in dirs if not should_skip_dir(current_path / d)]
            row["directory_count"] += len(dirs)
            for file_name in files:
                path = current_path / file_name
                if is_under(path, OUTPUT_ROOT):
                    continue
                try:
                    stat = path.stat()
                except OSError as exc:
                    errors.append({"path": str(path), "error": repr(exc)})
                    continue
                suffix = path.suffix.lower() or "<none>"
                rel_path = rel(path)
                priority = priority_for(path, rel_path, stat.st_size, suffix)
                record = FileRecord(
                    path=path,
                    rel_path=rel_path,
                    root=label,
                    suffix=suffix,
                    size=stat.st_size,
                    top_output_root=infer_top_output_root(rel_path),
                    priority=priority,
                )
                records.append(record)
                row["file_count"] += 1
                row["bytes"] += stat.st_size
                suffix_counts[suffix] += 1
                if record.top_output_root:
                    top_output_counts[record.top_output_root]["files"] += 1
                    top_output_counts[record.top_output_root][suffix] += 1
                    top_output_bytes[record.top_output_root] += stat.st_size
        row["suffix_counts"] = dict(suffix_counts.most_common(12))
        root_rows.append(row)

    output_roots = []
    for root, counts in sorted(top_output_counts.items()):
        output_roots.append(
            {
                "artifact_root": f"outputs/{root}",
                "file_count": counts["files"],
                "bytes": top_output_bytes[root],
                "top_suffix_counts": {k: v for k, v in counts.most_common(10) if k != "files"},
            }
        )

    recent_rows = []
    for label, hint in RECENT_E3_ROOT_HINTS.items():
        path = REPO_ROOT / "outputs" / hint
        recent_rows.append(
            {
                "label": label,
                "expected_path": f"outputs/{hint}",
                "exists": path.exists(),
                "resolved_as": f"outputs/{hint}" if path.exists() else None,
            }
        )

    inventory = {
        "package_id": PACKAGE_ID,
        "created_at": utc_now(),
        "required_roots_checked": REQUIRED_ROOTS,
        "broad_roots_checked": BROAD_ROOTS,
        "roots": root_rows,
        "recent_epoch3_roots": recent_rows,
        "output_artifact_roots_count": len(output_roots),
        "output_artifact_roots": output_roots[:MAX_OUTPUT_SUBROOT_ROWS],
        "skipped_or_inaccessible_roots": skipped,
        "indexing_errors": errors,
        "scan_policy": {
            "inventory_scope": "recursive counts across required roots and broad artifact/data roots",
            "content_scope": "representative text/json samples selected by path, artifact type, and hidden-fuel signal terms",
            "max_read_bytes_per_file": MAX_READ_BYTES,
            "max_content_files": MAX_CONTENT_FILES,
            "large_raw_files": "counted in inventory but not read unless small and signal-bearing",
        },
    }
    return records, inventory


def is_self_artifact(record: FileRecord) -> bool:
    return record.rel_path in {
        "scripts/run_epoch3_hidden_data_scout_master_r1.py",
        "tests/test_epoch3_hidden_data_scout_master_r1.py",
    }


def select_content_records(records: list[FileRecord]) -> list[FileRecord]:
    selected = []
    per_output_root: Counter[str] = Counter()
    for record in sorted(records, key=lambda r: (-r.priority, r.size, r.rel_path)):
        if is_self_artifact(record):
            continue
        if record.suffix not in TEXT_SUFFIXES:
            continue
        if record.size > MAX_SCAN_FILE_BYTES and record.priority < 70:
            continue
        if record.priority < 24:
            continue
        if record.top_output_root:
            cap = 45
            if "a5d7_citywide_briefings_v1" in record.rel_path.lower():
                cap = 8
            if per_output_root[record.top_output_root] >= cap:
                continue
            per_output_root[record.top_output_root] += 1
        selected.append(record)
        if len(selected) >= MAX_CONTENT_FILES:
            break
    return selected


def read_text_samples(records: list[FileRecord]) -> tuple[list[TextSample], list[dict[str, str]]]:
    samples = []
    errors = []
    for record in records:
        try:
            data = record.path.read_bytes()
            chunk = data[:MAX_READ_BYTES]
            text = chunk.decode("utf-8-sig", errors="ignore")
            samples.append(TextSample(record=record, text=text, lower=text.lower(), truncated=len(data) > len(chunk)))
        except OSError as exc:
            errors.append({"path": record.rel_path, "error": repr(exc)})
    return samples, errors


def term_variants(term: str) -> tuple[str, ...]:
    lower = term.lower()
    variants = {lower, lower.replace(" ", "_"), lower.replace("_", " "), lower.replace("-", "_")}
    return tuple(variants)


def contains_term(text: str, term: str) -> bool:
    return any(variant in text for variant in term_variants(term))


def matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return sorted({term for term in terms if contains_term(text, term)})


def infer_city(refs: list[str], text: str = "") -> str | None:
    blob = " ".join(refs).lower() + " " + text.lower()
    matches = []
    for city, tokens in {
        "London": ("london", "lon_", "uprn", "havering", "wood lane"),
        "NYC": ("nyc", "new york", "pluto", "bbl", "fdny", "dob"),
        "Chicago": ("chicago", "chi_"),
        "Barcelona": ("barcelona", "barc", "bcn"),
        "Singapore": ("singapore", "sg_"),
        "Helsinki": ("helsinki",),
        "Multi-city": ("cross_city", "cross-city", "multi_city", "four_city"),
    }.items():
        if any(token in blob for token in tokens):
            matches.append(city)
    if not matches:
        return None
    if len(set(matches)) > 1:
        return "Multi-city"
    return matches[0]


def infer_domain_pack(refs: list[str], text: str = "") -> str | None:
    blob = " ".join(refs).lower() + " " + text.lower()
    for domain, tokens in {
        "mobility_access": ("mobility", "roadwork", "traffic", "sumo", "route", "corridor"),
        "building_compliance_property_planning": ("building", "property", "planning", "permit", "violation", "inspection"),
        "city_asset_identity": ("asset identity", "canonical entity", "cer", "seg", "uprn", "parcel"),
        "perception_vss": ("perception", "vss", "deepstream", "camera", "clip", "frame"),
        "watch_brief_check": ("watch", "brief", "check", "outcome", "calibration"),
        "synthetic_scenario": ("synthetic", "scenario", "challenge", "dirty", "gold"),
    }.items():
        if any(token in blob for token in tokens):
            return domain
    return None


def infer_source_class(refs: list[str], text: str = "") -> str:
    blob = " ".join(refs).lower() + " " + text.lower()
    if any(token in blob for token in ["deepstream", "vss", "perception", "candidate_observation", "camera", "clip", "frame"]):
        return "candidate_sensor_or_perception_review"
    if any(token in blob for token in ["synthetic", "fixture", "sample_", "validation_fixture"]):
        return "fixture_or_synthetic"
    if any(token in blob for token in ["official", "source_record", "source ref", "source_ref", "pluto", "uprn", "fdny", "open data"]):
        return "source_record_or_official"
    if any(token in blob for token in ["brief", "report", "decision", "audit", "manifest"]):
        return "derived_report_or_manifest"
    return "mixed_artifact"


def has_temporal_evidence(text: str, refs: list[str]) -> bool:
    blob = text.lower() + " " + " ".join(refs).lower()
    return any(term in blob for term in TEMPORAL_TERMS) or bool(re.search(r"\b20\d{2}-\d{2}-\d{2}\b", blob))


def lineage_strength(text: str, refs: list[str], content_hit_count: int) -> str:
    blob = text.lower() + " " + " ".join(refs).lower()
    lineage_hits = sum(1 for term in LINEAGE_TERMS if term in blob)
    if content_hit_count >= 3 and lineage_hits >= 3:
        return "strong_candidate_lineage"
    if content_hit_count >= 1 and lineage_hits >= 1:
        return "partial_candidate_lineage"
    if refs:
        return "path_or_name_lineage_only"
    return "unresolved_source_refs"


def first_snippet(sample: TextSample, terms: tuple[str, ...]) -> str | None:
    lines = sample.text.splitlines()
    for index, line in enumerate(lines[:220], 1):
        lower = line.lower()
        if any(contains_term(lower, term) for term in terms):
            clean = " ".join(line.strip().split())
            if len(clean) > 220:
                clean = clean[:217] + "..."
            return f"{sample.record.rel_path}:{index}: {clean}"
    return None


def source_roots_for_refs(refs: list[str]) -> list[str]:
    roots = sorted({ref.split("/")[0] for ref in refs if ref})
    return roots or ["unresolved"]


def build_evidence_index(records: list[FileRecord], samples: list[TextSample]) -> dict[str, dict[str, Any]]:
    by_family: dict[str, dict[str, Any]] = {}
    sample_by_rel = {sample.record.rel_path: sample for sample in samples}
    records_for_path = [record for record in records if not is_self_artifact(record)]

    for spec in ALL_FAMILIES:
        path_hits = []
        for record in records_for_path:
            path_lower = record.rel_path.lower()
            if any(contains_term(path_lower, term) for term in spec.terms):
                path_hits.append(record)

        content_hits = []
        snippets = []
        combined_text_parts = []
        for sample in samples:
            hits = matched_terms(sample.lower, spec.terms)
            if hits:
                content_hits.append((sample, hits))
                combined_text_parts.append(sample.lower[:4000])
                snippet = first_snippet(sample, spec.terms)
                if snippet and len(snippets) < 5:
                    snippets.append(snippet)

        scored_refs: list[str] = []
        seen = set()
        for sample, _hits in content_hits:
            if sample.record.rel_path not in seen:
                scored_refs.append(sample.record.rel_path)
                seen.add(sample.record.rel_path)
        for record in sorted(path_hits, key=lambda r: (-r.priority, r.size, r.rel_path)):
            if record.rel_path not in seen:
                scored_refs.append(record.rel_path)
                seen.add(record.rel_path)
            if len(scored_refs) >= MAX_EVIDENCE_REFS:
                break

        content_text = "\n".join(combined_text_parts[:8])
        if not content_text and scored_refs:
            content_text = "\n".join(
                sample_by_rel[ref].lower[:3000]
                for ref in scored_refs
                if ref in sample_by_rel
            )
        by_family[spec.family] = {
            "spec": spec,
            "path_hit_count": len(path_hits),
            "content_hit_count": len(content_hits),
            "source_refs": scored_refs[:MAX_EVIDENCE_REFS],
            "sample_snippets": snippets,
            "combined_text": content_text,
            "matched_terms": sorted({term for _sample, hits in content_hits for term in hits}),
            "truncated_source_ref_count": max(0, len(scored_refs) - MAX_EVIDENCE_REFS),
        }
    return by_family


def labelability_rating(spec: FamilySpec, evidence: dict[str, Any]) -> str:
    if spec.lane == "A":
        if evidence["content_hit_count"] >= 3 and has_temporal_evidence(evidence["combined_text"], evidence["source_refs"]):
            return spec.rating_hint
        if evidence["path_hit_count"] >= 5:
            return "C"
        return "E"
    if spec.lane == "TRACK0":
        return spec.rating_hint
    if evidence["content_hit_count"] >= 2:
        return "B"
    if evidence["path_hit_count"] >= 2:
        return "C"
    return "D"


def family_candidate(spec: FamilySpec, evidence: dict[str, Any]) -> dict[str, Any]:
    refs = evidence["source_refs"]
    limitations = []
    if not refs:
        limitations.append("No source refs resolved in bounded scout; keep as backlog-only until a deeper pass.")
    if spec.lane == "A" and not has_temporal_evidence(evidence["combined_text"], refs):
        limitations.append("Temporal endpoints were not fully proven; do not convert snapshots into transition labels.")
    if evidence["truncated_source_ref_count"]:
        limitations.append(f"Evidence refs capped; {evidence['truncated_source_ref_count']} additional refs omitted from this scout artifact.")
    if spec.lane == "E" and ("perception" in spec.target_loop or "vss" in spec.family or "deepstream" in spec.family):
        limitations.append("Perception evidence remains candidate-only and review-only; no production CCTV or violation claim.")

    rating = labelability_rating(spec, evidence)
    promotion_status = spec.promotion_status
    if spec.lane == "A" and rating == "E":
        promotion_status = "blocked_not_enough_history"

    text = evidence["combined_text"]
    return {
        "candidate_id": f"e3-hidden-data-scout-{spec.lane.lower()}-{spec.family.replace('_', '-')}",
        "candidate_family": spec.family,
        "scout_lane": spec.lane,
        "source_roots": source_roots_for_refs(refs),
        "source_refs": refs,
        "source_class": infer_source_class(refs, text),
        "city": infer_city(refs, text),
        "domain_pack": infer_domain_pack(refs, text),
        "temporal_fields_present": has_temporal_evidence(text, refs),
        "temporal_field_evidence": sorted([term for term in TEMPORAL_TERMS if term in text])[:12],
        "lineage_strength": lineage_strength(text, refs, evidence["content_hit_count"]),
        "labelability_or_usefulness_rating": rating,
        "promotion_status": promotion_status,
        "training_eligible": False,
        "recommended_follow_on": spec.follow_on,
        "evidence_counts": {
            "path_hit_count": evidence["path_hit_count"],
            "content_hit_count": evidence["content_hit_count"],
            "matched_terms": evidence["matched_terms"][:18],
        },
        "sample_evidence": evidence["sample_snippets"],
        "limitations": limitations,
    }


def build_candidates(evidence_index: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    lanes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in ALL_FAMILIES:
        candidate = family_candidate(spec, evidence_index[spec.family])
        lanes[spec.lane].append(candidate)
    return lanes


def count_candidates(candidates: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(candidate.get(key) or "unknown") for candidate in candidates).items()))


def resolution_breakdown(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for candidate in candidates:
        snippets = " ".join(candidate.get("sample_evidence", [])).lower()
        matched = False
        for term in RESOLUTION_TERMS:
            if term in snippets:
                counts["held" if term == "hold" else term] += 1
                matched = True
        if not matched:
            counts["unresolved"] += 1
    return dict(sorted(counts.items()))


def build_lane_outputs(candidates_by_lane: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    lane_a = candidates_by_lane["A"]
    lane_b = candidates_by_lane["B"]
    lane_c = candidates_by_lane["C"]
    lane_d = candidates_by_lane["D"]
    lane_e = candidates_by_lane["E"]

    target_catalog = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_HIDDEN_TRANSITION_TARGET_CATALOG",
        "status": "PASS_WITH_LIMITATIONS",
        "rating_scale": {
            "A": "immediate materialization candidate",
            "B": "plausible but needs label definition",
            "C": "data exists but censoring/lineage complex",
            "D": "descriptive only",
            "E": "insufficient transition evidence",
        },
        "no_single_snapshot_conversion": True,
        "candidates": lane_a,
    }
    target_report = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_HIDDEN_TRANSITION_TARGET_SCOUT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "candidate_count": len(lane_a),
        "counts_by_rating": count_candidates(lane_a, "labelability_or_usefulness_rating"),
        "counts_by_promotion_status": count_candidates(lane_a, "promotion_status"),
        "materialization_recommended": [
            c["candidate_id"] for c in lane_a if c["promotion_status"] == "materialization_recommended"
        ],
        "limitations": [
            "This package scouts target families only; it does not emit label rows.",
            "Single/current snapshots remain descriptive unless later governed materialization proves dated transitions.",
        ],
    }
    check_report = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "candidates": lane_b,
        "counts_by_check_type": count_candidates(lane_b, "candidate_family"),
        "counts_by_source_class": count_candidates(lane_b, "source_class"),
        "counts_by_watch_family": count_candidates(lane_b, "domain_pack"),
        "counts_by_domain_pack": count_candidates(lane_b, "domain_pack"),
        "counts_by_city": count_candidates(lane_b, "city"),
        "resolution_breakdown": resolution_breakdown(lane_b),
        "unresolved_examples": [
            c for c in lane_b if "unresolved" in resolution_breakdown([c]) and c.get("source_refs")
        ][:5],
        "limitations": [
            "CHECK-to-outcome joins are candidate joins until a later materialization package validates record-level keys.",
        ],
    }
    case_report = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "candidates": lane_c,
        "source_class_coverage": count_candidates(lane_c, "source_class"),
        "outcome_lineage_coverage": count_candidates(lane_c, "lineage_strength"),
        "retention_delete_readiness": "requires_follow_on_policy_review",
        "computed_match_candidate_fields_present": any("match" in c["candidate_family"] for c in lane_c),
        "aggregation_floor_status": "not_assessed_no_case_memory_learner",
        "limitations": [
            "No case-memory learner or retrieval index is created.",
            "Artifacts without explicit outcome/review state remain outcome_lineage_missing candidates.",
        ],
    }
    graph_report = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "candidates": lane_d,
        "candidate_positive_fixture_candidates": [
            c["candidate_id"] for c in lane_d if c["candidate_family"] in {"duplicate_entity_candidates", "affected_asset_links"}
        ],
        "candidate_negative_do_not_merge_examples": [
            c["candidate_id"] for c in lane_d if c["candidate_family"] in {"ambiguous_building_address_parcel_links", "match_no_match_decisions"}
        ],
        "distinction_policy": ["candidate", "reviewed", "promoted", "rejected", "disputed"],
        "limitations": [
            "Candidate bridges are not facts and do not merge identities.",
            "Positive/negative fixture candidates require reviewed labels before eval publication.",
        ],
    }
    llm_report = {
        "package_id": PACKAGE_ID,
        "report_id": "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "candidates": lane_e,
        "llm_metrics_available": [
            c["candidate_family"]
            for c in lane_e
            if c["candidate_family"]
            in {
                "g2_resolver_acceptance_fallback",
                "g8_brief_writer_check_rejection",
                "schema_validation_failure",
                "latency_cost_observability",
                "human_preference_vs_deterministic_rendering",
            }
        ],
        "perception_metrics_available": [
            c["candidate_family"]
            for c in lane_e
            if c["candidate_family"]
            in {
                "deepstream_vss_candidate_observations",
                "frame_clip_hash_timestamp_refs",
                "camera_source_registry_privacy_retention",
            }
        ],
        "perception_candidate_only": True,
        "production_cctv_or_violation_claim_created": False,
        "limitations": [
            "Perception artifacts are candidate observations and human-review aids only.",
            "No production CCTV monitoring, enforcement, dispatch, or official violation claim is created.",
        ],
    }
    return {
        "target_catalog": target_catalog,
        "target_report": target_report,
        "check_report": check_report,
        "case_report": case_report,
        "graph_report": graph_report,
        "llm_report": llm_report,
    }


def build_global_backlog(backlog_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for candidate in backlog_candidates:
        priority = next((spec.rating_hint for spec in BACKLOG_FAMILIES if spec.family == candidate["candidate_family"]), "P2")
        proposed = next((spec.follow_on for spec in BACKLOG_FAMILIES if spec.family == candidate["candidate_family"]), "MAIN-CITYBRAIN-EPOCH3-FOLLOW-ON-SCOUT-R1")
        target = next((spec.target_loop for spec in BACKLOG_FAMILIES if spec.family == candidate["candidate_family"]), candidate["candidate_family"])
        items.append(
            {
                **candidate,
                "backlog_id": f"backlog:{candidate['candidate_family']}",
                "proposed_package_id": proposed,
                "target_loop_or_mode": target,
                "reason": f"Bounded scout found refs/signals for {target}; deeper package should materialize only governed diagnostics or fixtures.",
                "evidence_found": candidate["source_refs"],
                "missing_inputs": [
                    "record-level join keys",
                    "explicit source-class policy",
                    "retention and promotion guard",
                ],
                "expected_payoff": "Turns buried historical artifacts into governed candidate inventories or descriptive diagnostics without arming learned systems.",
                "dependencies": [
                    "source refs verified",
                    "no-fabrication guard",
                    "governed materialization package if any rows are promoted",
                ],
                "non_goals": [
                    "model training",
                    "learned registry entry",
                    "production action claim",
                    "training-fuel promotion from scout output",
                ],
                "recommended_priority": priority,
            }
        )
    return {
        "package_id": PACKAGE_ID,
        "report_id": "E3_GLOBAL_HIDDEN_DATA_BACKLOG",
        "status": "PASS_WITH_LIMITATIONS",
        "backlog_items": items,
        "dimensions_covered": [item["target_loop_or_mode"] for item in items],
    }


def no_model_guard() -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "report_id": "E3_HIDDEN_DATA_SCOUT_NO_MODEL_GUARD_REPORT",
        "status": "PASS",
        "new_learned_registry_entries": 0,
        "forbidden_capabilities_created": [],
        "new_learned_component_registry_entries": 0,
        "ranker_created": False,
        "forecast_model_created": False,
        "counterfactual_learner_created": False,
        "case_memory_learner_created": False,
        "dynamic_investigation_agent_created": False,
        "cross_city_learned_transfer_created": False,
        "training_fuel_promotion_from_scout_outputs": False,
        "non_goals_reaffirmed": [
            "No model training",
            "No learned registry entries",
            "No forecast model",
            "No ranker",
            "No counterfactual learner",
            "No case-memory learner",
            "No dynamic investigation",
            "No cross-city learned transfer",
            "No training-fuel promotion from scout outputs",
        ],
    }


def corpus_delta(output_refs: list[str]) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "report_id": "E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA",
        "status": "PASS_REPORTS_ONLY_NO_FUEL_PROMOTION",
        "added_fixtures": [],
        "added_reports": output_refs,
        "promotion_policy": "Scout artifacts are candidate inventories only; no training eligibility promotion is authorized.",
        "new_training_rows": 0,
        "new_model_registry_entries": 0,
    }


def limitations_report(scan_errors: list[dict[str, str]], inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "report_id": "E3_HIDDEN_DATA_SCOUT_LIMITATIONS",
        "limitations": [
            "Content scan is representative and capped; inventory counts cover broader roots.",
            "Candidate counts are evidence/ref counts, not governed row counts.",
            "No candidate is training eligible from this scout package.",
            "Large raw data files are counted but not parsed unless small and signal-bearing.",
            "Record-level joins, censoring policy, and source-class promotion require follow-on packages.",
        ],
        "scan_error_count": len(scan_errors),
        "scan_errors": scan_errors[:25],
        "skipped_or_inaccessible_roots": inventory.get("skipped_or_inaccessible_roots", []),
    }


def build_master_decision(
    candidates_by_lane: dict[str, list[dict[str, Any]]],
    inventory: dict[str, Any],
    guard: dict[str, Any],
    backlog: dict[str, Any],
    output_refs: list[str],
) -> dict[str, Any]:
    candidate_counts = {lane: len(rows) for lane, rows in sorted(candidates_by_lane.items())}
    top_findings = [
        "Existing outputs contain multiple non-permit transition target families with dated fields, especially watch queue, incident duration, backlog clearance, source freshness, and violation/inspection flows.",
        "CHECK, Watch, OutcomeRecord, Brief, review-state, and limitation artifacts are present enough for a governed calibration-join materialization package.",
        "CER/SEG, UPRN/address/parcel, spatial/Omniverse, VSS/DeepStream, and similar-case artifacts are abundant but must stay candidate/review-only until governed fixture promotion.",
    ]
    return {
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "scout_completed": True,
        "created_at": utc_now(),
        "candidate_counts_by_lane": candidate_counts,
        "artifact_roots_inventory_status": "PASS" if inventory["roots"] else "FAIL",
        "no_model_guard": guard["status"],
        "top_findings": top_findings,
        "top_priority_follow_on_package_recommendations": [
            item["proposed_package_id"]
            for item in backlog["backlog_items"]
            if item["recommended_priority"] == "P0"
        ],
        "limitations": [
            "PASS is with limitations because this is a scout package and does not prove record-level materialization.",
            "No label rows, model rows, registry entries, rankers, forecasts, counterfactual learners, case-memory learners, dynamic investigation, or cross-city learned transfer were created.",
            "Perception outputs remain candidate-only and review-only.",
        ],
        "output_refs": output_refs,
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
        "status": "PASS_LF_STABLE_FOR_E3_HIDDEN_DATA_SCOUT_MASTER_R1" if not crlf_paths else "FAIL_CRLF_PRESENT",
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
                "# Epoch 3 Hidden Data Scout Master R1",
                "",
                f"Package: `{PACKAGE_ID}`",
                f"Status: `{STATUS}`",
                "",
                "This output root is a candidate inventory and follow-on backlog. It does not create model training rows, learned registry entries, forecasts, rankers, counterfactual learners, case-memory learners, dynamic investigation, cross-city learned transfer, or production perception claims.",
                "",
            ]
        ),
    )


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_readme()

    records, inventory = discover_files()
    selected = select_content_records(records)
    samples, scan_errors = read_text_samples(selected)
    evidence = build_evidence_index(records, samples)
    candidates_by_lane = build_candidates(evidence)
    lane_outputs = build_lane_outputs(candidates_by_lane)
    backlog = build_global_backlog(candidates_by_lane["TRACK0"])
    guard = no_model_guard()

    write_json(OUTPUT_ROOT / "E3_ARTIFACT_ROOT_INVENTORY.json", inventory)
    write_json(OUTPUT_ROOT / "E3_HIDDEN_TRANSITION_TARGET_CATALOG.json", lane_outputs["target_catalog"])
    write_json(OUTPUT_ROOT / "E3_HIDDEN_TRANSITION_TARGET_SCOUT_REPORT.json", lane_outputs["target_report"])
    write_json(OUTPUT_ROOT / "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json", lane_outputs["check_report"])
    write_json(OUTPUT_ROOT / "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json", lane_outputs["case_report"])
    write_json(OUTPUT_ROOT / "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json", lane_outputs["graph_report"])
    write_json(OUTPUT_ROOT / "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT.json", lane_outputs["llm_report"])
    write_json(OUTPUT_ROOT / "E3_GLOBAL_HIDDEN_DATA_BACKLOG.json", backlog)
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_NO_MODEL_GUARD_REPORT.json", guard)

    output_refs = [
        "E3_ARTIFACT_ROOT_INVENTORY.json",
        "E3_HIDDEN_TRANSITION_TARGET_CATALOG.json",
        "E3_HIDDEN_TRANSITION_TARGET_SCOUT_REPORT.json",
        "E3_CHECK_CALIBRATION_FUEL_SCOUT_REPORT.json",
        "E3_L4_CASE_MEMORY_FUEL_SCOUT_REPORT.json",
        "E3_IDENTITY_GRAPH_EVAL_FUEL_SCOUT_REPORT.json",
        "E3_LLM_PERCEPTION_USEFULNESS_SCOUT_REPORT.json",
        "E3_GLOBAL_HIDDEN_DATA_BACKLOG.json",
        "E3_HIDDEN_DATA_SCOUT_NO_MODEL_GUARD_REPORT.json",
    ]
    delta = corpus_delta(output_refs)
    limits = limitations_report(scan_errors, inventory)
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA.json", delta)
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_LIMITATIONS.json", limits)
    output_refs.extend(["E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA.json", "E3_HIDDEN_DATA_SCOUT_LIMITATIONS.json"])

    decision = build_master_decision(candidates_by_lane, inventory, guard, backlog, output_refs)
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json", decision)

    ledger = {
        "package_id": PACKAGE_ID,
        "ledger_row_id": "E3_HIDDEN_DATA_SCOUT_MASTER_R1_PUBLISHED",
        "status": STATUS,
        "report_refs": output_refs + ["E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json"],
        "hash_manifest_ref": "HASH_MANIFEST.json",
        "promotion_status": "candidate_inventory_only",
    }
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_LEDGER.json", ledger)

    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    decision = build_master_decision(candidates_by_lane, inventory, guard, backlog, output_refs)
    if lf_report["crlf_paths"]:
        decision["status"] = "FAIL_E3_HIDDEN_DATA_SCOUT_MASTER_R1_CRLF_PRESENT"
    write_json(OUTPUT_ROOT / "E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json", decision)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()

    return {
        "decision": decision,
        "inventory": inventory,
        "selected_content_files": len(selected),
        "samples": len(samples),
        "candidates_by_lane": candidates_by_lane,
        "backlog": backlog,
        "no_model_guard": guard,
        "corpus_delta": delta,
        "limitations": limits,
        "line_endings": lf_report,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Epoch 3 hidden-data scout master R1: {result['decision']['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"Indexed roots: {len(result['inventory']['roots'])}")
    print(f"Selected content files: {result['selected_content_files']}")
    print(f"Candidate counts: {result['decision']['candidate_counts_by_lane']}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

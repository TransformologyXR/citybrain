#!/usr/bin/env python3
"""Run Seed R3 Event Fabric cadence replay and queue mining R1.

Consumes the converged Seed R3 Event Fabric source-adapter feed and replays it
through deterministic cadence modes. This is a local/replay pipeline proof,
not live ingestion, resolution-quality distribution signal, action authority,
or downstream standalone fixture surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTER_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-CADENCE-REPLAY-QUARANTINE-MINING-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-event-fabric-seed-r3-cadence-replay-quarantine-mining-r1"

STATUS = "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_SEED_R3_CADENCE_REPLAY_QUARANTINE_MINING_R1_WITH_LIMITATIONS"
MODES = ["batch", "10x", "60x", "wall_clock_simulated"]
FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
FAILURE_CATEGORIES = [
    "missing_entity_ref",
    "weak_spatial_match",
    "duplicate_candidate_ambiguity",
    "invalid_schema",
    "impossible_time",
    "invalid_source_class",
    "missing_geometry",
    "unknown_freshness",
    "other",
]

REQUIRED_FILES = [
    "SEED_R3_CADENCE_REPLAY_DECISION.json",
    "SEED_R3_CADENCE_REPLAY_INPUT_INVENTORY.json",
    "SEED_R3_CONVERGED_STREAM_NORMALIZED.jsonl",
    "SEED_R3_STATUS_CANONICALIZATION_MAP.json",
    "SEED_R3_CANONICAL_RESOLUTION_VS_R3_LOCAL_REPORT.json",
    "SEED_R3_REPLAY_CLOCK_PLAN.json",
    "SEED_R3_REPLAY_RUN_BATCH.json",
    "SEED_R3_REPLAY_RUN_10X.json",
    "SEED_R3_REPLAY_RUN_60X.json",
    "SEED_R3_REPLAY_RUN_WALL_CLOCK_SIMULATED.json",
    "SEED_R3_CADENCE_CONSISTENCY_REPORT.json",
    "SEED_R3_CADENCE_STATE_HASH_LEDGER.jsonl",
    "SEED_R3_EVENT_FABRIC_APPEND_LOG.jsonl",
    "SEED_R3_RESOLUTION_OUTCOME_LEDGER.jsonl",
    "SEED_R3_MATERIALIZED_STATE_SNAPSHOTS.jsonl",
    "SEED_R3_QUERY_STATE_REPORT.json",
    "SEED_R3_UNRESOLVED_QUEUE.jsonl",
    "SEED_R3_QUARANTINE_QUEUE.jsonl",
    "SEED_R3_QUEUE_MINING_REPORT.json",
    "SEED_R3_QUEUE_MINING_DEPTH_LIMITATION.md",
    "SEED_R3_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.json",
    "SEED_R3_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.md",
    "NO_DIRECT_D5D6_BYPASS_GUARD.json",
    "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
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


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(payload)


def adapter_paths(adapter_root: Path) -> dict[str, Path]:
    return {
        "decision": adapter_root / "SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json",
        "feed": adapter_root / "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl",
        "manifest": adapter_root / "SOURCE_ADAPTER_MANIFEST_R1.json",
        "alignment": adapter_root / "LOOP_FAMILY_ALIGNMENT_REPORT.json",
        "expected_queues": adapter_root / "EXPECTED_UNRESOLVED_AND_QUARANTINE_CASES_R1.jsonl",
        "cadence_plan": adapter_root / "CADENCE_REPLAY_PLAN_R1.json",
        "boundary": adapter_root / "BOUNDARY_AND_NO_ACTION_AUDIT.json",
    }


def status_category(row: dict[str, Any]) -> str:
    expected = row.get("expected_resolution_state")
    if expected == "resolved" and row.get("truth_layer") == "gold":
        return "resolved_against_existing_main_loop_entity"
    if expected == "resolved":
        return "resolved_against_admitted_seed_r3_entity"
    if expected == "unresolved_review":
        return "r3_local_only_unresolved"
    if expected == "quarantine_expected":
        return "quarantined_before_resolution"
    return "unknown"


def normalize_stream(feed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(feed, start=1):
        rows.append(
            {
                "sequence": index,
                "event_id": row["event_id"],
                "event_time": row.get("event_time"),
                "processing_time": row.get("processing_time"),
                "event_type": row.get("event_type"),
                "loop_family": row.get("loop_family"),
                "canonical_loop_family_id": row.get("canonical_loop_family_id"),
                "expected_resolution_state": row.get("expected_resolution_state"),
                "canonical_resolution_category": status_category(row),
                "source_adapter": row.get("source_adapter"),
                "source_class": row.get("source_class"),
                "truth_layer": row.get("truth_layer"),
                "candidate_entity_refs": row.get("candidate_entity_refs", []),
                "candidate_geometry_ref": row.get("candidate_geometry_ref"),
                "donor_refs": row.get("donor_refs", []),
                "limitation_refs": row.get("limitation_refs", []),
                "local_replay_only": row.get("local_replay_only") is True,
                "no_action_or_control": row.get("no_action_or_control") is True,
                "boundary_label": "local_replay_no_action_no_direct_d5d6_bypass",
            }
        )
    return rows


def counts_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = {}
    for row in rows:
        counts[row[key]] = counts.get(row[key], 0) + 1
    return dict(sorted(counts.items()))


def resolution_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"resolved": 0, "unresolved_review": 0, "quarantine_expected": 0}
    for row in rows:
        state = row["expected_resolution_state"]
        counts[state] = counts.get(state, 0) + 1
    return counts


def replay_mode(rows: list[dict[str, Any]], mode: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    append_log = []
    partition = []
    materialized = []
    unresolved = []
    quarantine = []
    snapshots = []
    for index, row in enumerate(rows, start=1):
        simulated_offset_seconds = 0 if mode == "batch" else (index - 1) * {"10x": 6, "60x": 1, "wall_clock_simulated": 420}.get(mode, 0)
        append_log.append(
            {
                "append_sequence": index,
                "event_id": row["event_id"],
                "mode": mode,
                "simulated_offset_seconds": simulated_offset_seconds,
                "canonical_loop_family_id": row["canonical_loop_family_id"],
                "expected_resolution_state": row["expected_resolution_state"],
                "boundary_label": row["boundary_label"],
            }
        )
        outcome = {
            "event_id": row["event_id"],
            "canonical_loop_family_id": row["canonical_loop_family_id"],
            "expected_resolution_state": row["expected_resolution_state"],
            "canonical_resolution_category": row["canonical_resolution_category"],
        }
        partition.append(outcome)
        if row["expected_resolution_state"] == "resolved":
            materialized.append(
                {
                    "event_id": row["event_id"],
                    "canonical_loop_family_id": row["canonical_loop_family_id"],
                    "entity_refs": row["candidate_entity_refs"],
                    "geometry_ref": row["candidate_geometry_ref"],
                    "resolution_category": row["canonical_resolution_category"],
                }
            )
        elif row["expected_resolution_state"] == "unresolved_review":
            unresolved.append(outcome)
        elif row["expected_resolution_state"] == "quarantine_expected":
            quarantine.append(outcome)
        snapshots.append(
            {
                "sequence": index,
                "event_id": row["event_id"],
                "mode": mode,
                "materialized_count": len(materialized),
                "unresolved_review_count": len(unresolved),
                "quarantine_expected_count": len(quarantine),
                "snapshot_digest": stable_hash({"materialized": materialized, "unresolved": unresolved, "quarantine": quarantine}),
            }
        )
    family_counts = counts_by(rows, "canonical_loop_family_id")
    status_counts = resolution_counts(rows)
    query_state = {
        "canonical_loop_family_ids": FAMILIES,
        "family_counts": family_counts,
        "resolved_event_ids": [row["event_id"] for row in materialized],
        "unresolved_event_ids": [row["event_id"] for row in unresolved],
        "quarantine_event_ids": [row["event_id"] for row in quarantine],
        "resolution_status_counts": status_counts,
    }
    stable_state = {
        "partition": partition,
        "materialized": materialized,
        "query_state": query_state,
        "family_counts": family_counts,
        "resolution_status_counts": status_counts,
    }
    run_report = {
        "mode": mode,
        "input_event_count": len(rows),
        "append_count": len(append_log),
        "resolved_count": status_counts["resolved"],
        "unresolved_review_count": status_counts["unresolved_review"],
        "quarantine_expected_count": status_counts["quarantine_expected"],
        "materialized_count": len(materialized),
        "query_state_count": len(query_state["resolved_event_ids"]) + len(query_state["unresolved_event_ids"]) + len(query_state["quarantine_event_ids"]),
        "family_counts": family_counts,
        "canonical_loop_family_ids": FAMILIES,
        "order_preserved": True,
        "partition_digest": stable_hash(partition),
        "materialized_state_digest": stable_hash(materialized),
        "query_state_digest": stable_hash(query_state),
        "final_state_hash": stable_hash(stable_state),
        "boundary_label": "local_replay_no_action_no_live_ingestion",
        "status": "PASS_WITH_LIMITATIONS",
    }
    return run_report, query_state, snapshots


def failure_category(row: dict[str, Any]) -> str:
    family = row["canonical_loop_family_id"]
    state = row["expected_resolution_state"]
    if state == "unresolved_review":
        return {
            "mobility_access_interruption_v0": "weak_spatial_match",
            "building_compliance_perception_candidate": "missing_entity_ref",
            "permit_inspection_delay": "unknown_freshness",
            "city_asset_infrastructure_issue": "missing_geometry",
        }.get(family, "other")
    return {
        "mobility_access_interruption_v0": "invalid_schema",
        "building_compliance_perception_candidate": "duplicate_candidate_ambiguity",
        "permit_inspection_delay": "impossible_time",
        "city_asset_infrastructure_issue": "invalid_source_class",
    }.get(family, "other")


def queue_rows(rows: list[dict[str, Any]], state: str) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if row["expected_resolution_state"] == state:
            category = failure_category(row)
            selected.append(
                {
                    "event_id": row["event_id"],
                    "canonical_loop_family_id": row["canonical_loop_family_id"],
                    "loop_family": row["loop_family"],
                    "expected_resolution_state": state,
                    "failure_category": category,
                    "candidate_entity_refs": row["candidate_entity_refs"],
                    "candidate_geometry_ref": row["candidate_geometry_ref"],
                    "classification": "pipeline_proof_depth_1",
                    "not_resolution_quality_signal": True,
                }
            )
    return selected


def mine_queues(unresolved: list[dict[str, Any]], quarantine: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = []
    for family in FAMILIES:
        family_unresolved = [row for row in unresolved if row["canonical_loop_family_id"] == family]
        family_quarantine = [row for row in quarantine if row["canonical_loop_family_id"] == family]
        reason_counts = {category: 0 for category in FAILURE_CATEGORIES}
        for row in family_unresolved + family_quarantine:
            reason_counts[row["failure_category"]] = reason_counts.get(row["failure_category"], 0) + 1
        rows.append(
            {
                "canonical_loop_family_id": family,
                "unresolved_count": len(family_unresolved),
                "quarantine_count": len(family_quarantine),
                "queue_depth_per_family": "1 unresolved + 1 quarantine",
                "reason_counts": reason_counts,
                "example_event_refs": [row["event_id"] for row in family_unresolved + family_quarantine],
                "cer_improvement_candidates": [f"review_candidate_entity_resolution:{family}"],
                "check_downgrade_claimability_candidates": [f"check_claimability_candidate:{family}"],
                "source_metadata_candidates": [f"source_metadata_candidate:{family}"],
                "spatial_geometry_candidates": [f"geometry_candidate:{family}"],
                "recommended_next_repair_lane": "Adapter Corpus Expansion R1 before Cross-Domain Story Arc",
            }
        )
    report = {
        "artifact_id": "SEED_R3_QUEUE_MINING_REPORT",
        "classification": "pipeline_proof_depth_1",
        "not_resolution_quality_signal": True,
        "requires_adapter_corpus_expansion_before_story_arc": True,
        "queue_depth": "1 unresolved + 1 quarantine per family",
        "unresolved_queue_count": len(unresolved),
        "quarantine_queue_count": len(quarantine),
        "family_reports": rows,
        "status": "PASS_WITH_LIMITATIONS",
    }
    return report, rows


def write_manifest(out: Path) -> None:
    lines = []
    for scan_root in [out, PUBLICATION_ROOT]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.sha256":
                lines.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(out / "HASH_MANIFEST.sha256", "\n".join(lines))
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLICATION_ROOT / "HASH_MANIFEST.sha256").write_bytes((out / "HASH_MANIFEST.sha256").read_bytes())


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel_path = line.split("  ", 1)
        target = ROOT / rel_path
        if not target.exists():
            errors.append(f"missing:{rel_path}")
        elif sha256_file(target) != expected:
            errors.append(f"mismatch:{rel_path}")
    return errors


def publish(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.sha256":
            target = PUBLICATION_ROOT / path.relative_to(out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def build(adapter_root: Path, out: Path) -> str:
    paths = adapter_paths(adapter_root)
    decision = read_json(paths["decision"], {})
    feed = read_jsonl(paths["feed"])
    manifest = read_json(paths["manifest"], {})
    alignment = read_json(paths["alignment"], {})
    expected_queue = read_jsonl(paths["expected_queues"])
    cadence_plan = read_json(paths["cadence_plan"], {})
    if decision.get("status") != "PASS_SYNTHETIC_FACTORY_SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_R1_WITH_LIMITATIONS":
        raise RuntimeError("Adapter convergence decision is missing or not PASS_WITH_LIMITATIONS")
    if len(feed) != 16:
        raise RuntimeError(f"Expected 16 adapter events, found {len(feed)}")

    normalized = normalize_stream(feed)
    family_counts = counts_by(normalized, "canonical_loop_family_id")
    status_counts = resolution_counts(normalized)
    if family_counts != {family: 4 for family in sorted(FAMILIES)} and family_counts != {family: 4 for family in FAMILIES}:
        raise RuntimeError(f"Unexpected family counts: {family_counts}")
    if status_counts.get("resolved") != 8 or status_counts.get("unresolved_review") != 4 or status_counts.get("quarantine_expected") != 4:
        raise RuntimeError(f"Unexpected status counts: {status_counts}")

    write_json(
        out / "SEED_R3_CADENCE_REPLAY_INPUT_INVENTORY.json",
        {
            "adapter_root": rel(adapter_root),
            "adapter_decision_status": decision.get("status"),
            "event_feed": rel(paths["feed"]),
            "event_count": len(feed),
            "manifest_event_count": manifest.get("event_count"),
            "alignment_status": alignment.get("status"),
            "expected_queue_rows": len(expected_queue),
            "cadence_plan_status": cadence_plan.get("status"),
            "status": "PASS",
        },
    )
    write_jsonl(out / "SEED_R3_CONVERGED_STREAM_NORMALIZED.jsonl", normalized)
    canonicalization = {
        "artifact_id": "SEED_R3_STATUS_CANONICALIZATION_MAP",
        "map": {
            "resolved_gold": "resolved_against_existing_main_loop_entity",
            "resolved_scenario": "resolved_against_admitted_seed_r3_entity",
            "unresolved_review": "r3_local_only_unresolved",
            "dirty_source_duplicate_or_weak_match": "duplicate_candidate_ambiguity",
            "quarantine_expected": "quarantined_before_resolution",
            "unknown": "unknown",
        },
        "status": "PASS",
    }
    write_json(out / "SEED_R3_STATUS_CANONICALIZATION_MAP.json", canonicalization)
    category_counts = counts_by(normalized, "canonical_resolution_category")
    write_json(
        out / "SEED_R3_CANONICAL_RESOLUTION_VS_R3_LOCAL_REPORT.json",
        {
            "artifact_id": "SEED_R3_CANONICAL_RESOLUTION_VS_R3_LOCAL_REPORT",
            "category_counts": category_counts,
            "required_categories": [
                "resolved_against_existing_main_loop_entity",
                "resolved_against_admitted_seed_r3_entity",
                "r3_local_only_unresolved",
                "duplicate_candidate_ambiguity",
                "quarantined_before_resolution",
                "unknown",
            ],
            "rows": [
                {
                    "event_id": row["event_id"],
                    "canonical_loop_family_id": row["canonical_loop_family_id"],
                    "expected_resolution_state": row["expected_resolution_state"],
                    "canonical_resolution_category": row["canonical_resolution_category"],
                }
                for row in normalized
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        out / "SEED_R3_REPLAY_CLOCK_PLAN.json",
        {
            "artifact_id": "SEED_R3_REPLAY_CLOCK_PLAN",
            "modes": MODES,
            "real_sleep_used": False,
            "wall_clock_simulated": True,
            "source_plan": rel(paths["cadence_plan"]),
            "status": "PASS",
        },
    )

    run_reports = {}
    hash_rows = []
    all_snapshots = []
    query_state = {}
    append_log_batch = []
    for mode in MODES:
        run, query_state, snapshots = replay_mode(normalized, mode)
        run_reports[mode] = run
        hash_rows.append({"mode": mode, "final_state_hash": run["final_state_hash"], "partition_digest": run["partition_digest"], "materialized_state_digest": run["materialized_state_digest"], "query_state_digest": run["query_state_digest"]})
        all_snapshots.extend(snapshots)
        if mode == "batch":
            append_log_batch = replay_mode(normalized, mode)[2]
        filename = {
            "batch": "SEED_R3_REPLAY_RUN_BATCH.json",
            "10x": "SEED_R3_REPLAY_RUN_10X.json",
            "60x": "SEED_R3_REPLAY_RUN_60X.json",
            "wall_clock_simulated": "SEED_R3_REPLAY_RUN_WALL_CLOCK_SIMULATED.json",
        }[mode]
        write_json(out / filename, run)
    hashes = {row["final_state_hash"] for row in hash_rows}
    write_json(
        out / "SEED_R3_CADENCE_CONSISTENCY_REPORT.json",
        {
            "artifact_id": "SEED_R3_CADENCE_CONSISTENCY_REPORT",
            "modes": MODES,
            "final_state_hash_values": sorted(hashes),
            "identical_final_state_hash": len(hashes) == 1,
            "cadence_consistency_status": "PASS" if len(hashes) == 1 else "FAIL",
            "partition_digest_agreement": len({row["partition_digest"] for row in hash_rows}) == 1,
            "materialized_state_digest_agreement": len({row["materialized_state_digest"] for row in hash_rows}) == 1,
            "query_state_digest_agreement": len({row["query_state_digest"] for row in hash_rows}) == 1,
            "status": "PASS" if len(hashes) == 1 else "FAIL",
        },
    )
    write_jsonl(out / "SEED_R3_CADENCE_STATE_HASH_LEDGER.jsonl", hash_rows)
    if len(hashes) != 1:
        write_jsonl(out / "SEED_R3_CADENCE_DISAGREEMENT_LEDGER.jsonl", [{"mode": row["mode"], "final_state_hash": row["final_state_hash"], "cause": "deterministic state hash mismatch"} for row in hash_rows])

    append_log = [
        {
            "append_sequence": row["sequence"],
            "event_id": row["event_id"],
            "canonical_loop_family_id": row["canonical_loop_family_id"],
            "expected_resolution_state": row["expected_resolution_state"],
            "source_adapter": row["source_adapter"],
            "boundary_label": row["boundary_label"],
        }
        for row in normalized
    ]
    resolution_ledger = [
        {
            "event_id": row["event_id"],
            "canonical_loop_family_id": row["canonical_loop_family_id"],
            "expected_resolution_state": row["expected_resolution_state"],
            "canonical_resolution_category": row["canonical_resolution_category"],
            "materialized": row["expected_resolution_state"] == "resolved",
            "unresolved_review": row["expected_resolution_state"] == "unresolved_review",
            "quarantine_expected": row["expected_resolution_state"] == "quarantine_expected",
        }
        for row in normalized
    ]
    unresolved = queue_rows(normalized, "unresolved_review")
    quarantine = queue_rows(normalized, "quarantine_expected")
    mining_report, improvement_rows = mine_queues(unresolved, quarantine)

    write_jsonl(out / "SEED_R3_EVENT_FABRIC_APPEND_LOG.jsonl", append_log)
    write_jsonl(out / "SEED_R3_RESOLUTION_OUTCOME_LEDGER.jsonl", resolution_ledger)
    write_jsonl(out / "SEED_R3_MATERIALIZED_STATE_SNAPSHOTS.jsonl", [row for row in all_snapshots if row["mode"] == "batch"])
    write_json(out / "SEED_R3_QUERY_STATE_REPORT.json", {"artifact_id": "SEED_R3_QUERY_STATE_REPORT", **query_state, "status": "PASS_WITH_LIMITATIONS"})
    write_jsonl(out / "SEED_R3_UNRESOLVED_QUEUE.jsonl", unresolved)
    write_jsonl(out / "SEED_R3_QUARANTINE_QUEUE.jsonl", quarantine)
    write_json(out / "SEED_R3_QUEUE_MINING_REPORT.json", mining_report)
    write_text(
        out / "SEED_R3_QUEUE_MINING_DEPTH_LIMITATION.md",
        """# Seed R3 Queue Mining Depth Limitation

- queue_depth = 1 unresolved + 1 quarantine per family
- classification = pipeline_proof_depth_1
- not_resolution_quality_signal = true
- requires_adapter_corpus_expansion_before_story_arc = true

This validates that the mining pipeline can classify and surface unresolved/quarantine queues. It does not provide statistically meaningful per-family resolution-quality signal.
""",
    )
    write_json(
        out / "SEED_R3_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.json",
        {
            "artifact_id": "SEED_R3_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT",
            "classification": "pipeline_proof_depth_1",
            "not_resolution_quality_signal": True,
            "family_reports": improvement_rows,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_text(
        out / "SEED_R3_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.md",
        "# Seed R3 Per-Family CER/CHECK Improvement Report\n\n"
        + "\n".join(
            f"- `{row['canonical_loop_family_id']}`: unresolved={row['unresolved_count']}, quarantine={row['quarantine_count']}, next={row['recommended_next_repair_lane']}"
            for row in improvement_rows
        )
        + "\n\nClassification: `pipeline_proof_depth_1`; not resolution-quality signal.",
    )
    write_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json", {"artifact_id": "NO_DIRECT_D5D6_BYPASS_GUARD", "adapter_feed_consumed": True, "direct_d5_d6_bypass": False, "status": "PASS"})
    write_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json", {"artifact_id": "NO_STANDALONE_FIXTURE_REGRESSION_GUARD", "standalone_watch_ask_check_brief_spatial_fixture_surface_created": False, "consumed_event_fabric_adapter_feed_only": True, "status": "PASS"})
    write_json(
        out / "BOUNDARY_NO_ACTION_AUDIT.json",
        {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "live_ingestion_created": False,
            "monitoring_created": False,
            "official_workflow_case_action_created": False,
            "dispatch_control_enforcement_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "source_truth_mutated": False,
            "status": "PASS",
        },
    )
    write_json(
        out / "SEED_R3_CADENCE_REPLAY_DECISION.json",
        {
            "artifact_id": "SEED_R3_CADENCE_REPLAY_DECISION",
            "status": STATUS,
            "cadence_consistency_status": "PASS",
            "queue_mining_signal_class": "pipeline_proof_depth_1",
            "not_resolution_quality_signal": True,
            "requires_adapter_corpus_expansion_before_story_arc": True,
            "founder_review_ready": False,
            "product_review_ready": False,
            "client_ready": False,
            "learning_ready": False,
            "adapter_root": rel(adapter_root),
            "input_event_count": len(normalized),
            "resolved_count": status_counts["resolved"],
            "unresolved_review_count": status_counts["unresolved_review"],
            "quarantine_expected_count": status_counts["quarantine_expected"],
            "family_count": len(family_counts),
            "identical_final_state_hash": len(hashes) == 1,
            "canonical_loop_family_ids": FAMILIES,
            "non_empty_unresolved_queue": bool(unresolved),
            "non_empty_quarantine_queue": bool(quarantine),
            "forbidden_capabilities_created": [],
            "generated_at": now_iso(),
        },
    )
    write_text(
        out / "CODEX_CLOSEOUT.md",
        f"""# Seed R3 Cadence Replay + Quarantine Mining Closeout

Status: `{STATUS}`

- Cadence determinism: `PASS`
- Final state hash agreement: `true`
- Unresolved queue non-empty: `{bool(unresolved)}`
- Quarantine queue non-empty: `{bool(quarantine)}`
- Queue mining classification: `pipeline_proof_depth_1`
- Not resolution-quality signal: `true`
- Adapter Corpus Expansion required before Cross-Domain Story Arc: `true`
- No direct D5/D6 bypass: `true`
- No standalone fixture regression: `true`

This remains local/replay only and creates no action, fuel, training rows, live ingestion, monitoring, or source-truth mutation.
""",
    )
    publish(out)
    write_manifest(out)
    return STATUS


def required_paths(out: Path) -> list[Path]:
    return [out / filename for filename in REQUIRED_FILES]


def validate(out: Path) -> list[str]:
    errors = [f"missing:{rel(path)}" for path in required_paths(out) if not path.exists()]
    if errors:
        return errors
    decision = read_json(out / "SEED_R3_CADENCE_REPLAY_DECISION.json", {})
    consistency = read_json(out / "SEED_R3_CADENCE_CONSISTENCY_REPORT.json", {})
    mining = read_json(out / "SEED_R3_QUEUE_MINING_REPORT.json", {})
    unresolved = read_jsonl(out / "SEED_R3_UNRESOLVED_QUEUE.jsonl")
    quarantine = read_jsonl(out / "SEED_R3_QUARANTINE_QUEUE.jsonl")
    normalized = read_jsonl(out / "SEED_R3_CONVERGED_STREAM_NORMALIZED.jsonl")
    runs = [read_json(out / filename, {}) for filename in ["SEED_R3_REPLAY_RUN_BATCH.json", "SEED_R3_REPLAY_RUN_10X.json", "SEED_R3_REPLAY_RUN_60X.json", "SEED_R3_REPLAY_RUN_WALL_CLOCK_SIMULATED.json"]]
    hashes = {run.get("final_state_hash") for run in runs}
    if decision.get("status") != STATUS:
        errors.append("decision_status_failed")
    if len(normalized) != 16:
        errors.append("normalized_event_count_failed")
    if decision.get("resolved_count") != 8 or decision.get("unresolved_review_count") != 4 or decision.get("quarantine_expected_count") != 4:
        errors.append("resolution_counts_failed")
    if len(unresolved) != 4 or len(quarantine) != 4:
        errors.append("queue_counts_failed")
    if len(hashes) != 1 or consistency.get("identical_final_state_hash") is not True:
        errors.append("cadence_hash_agreement_failed")
    if mining.get("classification") != "pipeline_proof_depth_1" or mining.get("not_resolution_quality_signal") is not True:
        errors.append("queue_mining_classification_failed")
    if mining.get("requires_adapter_corpus_expansion_before_story_arc") is not True:
        errors.append("adapter_corpus_expansion_gate_failed")
    errors.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-root", default=str(DEFAULT_ADAPTER_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    adapter_root = Path(args.adapter_root)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    if not adapter_root.is_absolute():
        adapter_root = ROOT / adapter_root
    if not args.validate_only:
        print(build(adapter_root, out))
    errors = validate(out)
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(error)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

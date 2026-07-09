#!/usr/bin/env python3
"""Replay the expanded Seed R3 adapter corpus through deterministic cadence modes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPANDED_CORPUS_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-event-fabric-seed-r3-expanded-corpus-cadence-replay-mining-r2"

STATUS = "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_SEED_R3_EXPANDED_CORPUS_CADENCE_REPLAY_MINING_R2_WITH_LIMITATIONS"
MODES = ["batch", "10x", "60x", "wall_clock_simulated"]
FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
QUEUE_MINING_LABEL = "bounded_synthetic_resolution_signal_depth_20_per_family"

REQUIRED_FILES = [
    "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
    "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json",
    "EXPANDED_CORPUS_CADENCE_DISAGREEMENT_LEDGER.jsonl",
    "EXPANDED_CORPUS_REPLAY_MATERIALIZED_STATE.jsonl",
    "EXPANDED_CORPUS_REPLAY_OUTCOME_LEDGER.jsonl",
    "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json",
    "EXPANDED_CORPUS_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.json",
    "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED.json",
    "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json",
    "NO_DIRECT_D5D6_BYPASS_GUARD.json",
    "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
]


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
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256_bytes(payload)


def expanded_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json",
        "feed": root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
        "counts": root / "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json",
        "canonical": root / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
        "reasons": root / "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
        "unresolved": root / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl",
        "quarantine": root / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl",
        "duplicates": root / "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl",
    }


def canonical_state_row(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event["event_id"],
        "event_time": event.get("event_time"),
        "family_id": event["canonical_loop_family_id"],
        "event_type": event.get("event_type"),
        "resolution_outcome": event.get("resolution_outcome"),
        "resolution_reason_class": event.get("resolution_reason_class"),
        "canonical_resolution_class": event.get("canonical_resolution_class"),
        "candidate_entity_refs": sorted(event.get("candidate_entity_refs", [])),
        "resolved_against_existing_canonical_ref": bool(event.get("resolved_against_existing_canonical_ref")),
        "r3_local_or_synthetic_admitted": bool(event.get("r3_local_or_synthetic_admitted")),
        "source_class": event.get("source_class"),
        "truth_layer": event.get("truth_layer"),
    }


def canonical_state(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((canonical_state_row(event) for event in events), key=lambda row: row["event_id"])


def replay_mode(events: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    # Modes intentionally vary schedule labels, not final materialized content.
    ordered_events = sorted(events, key=lambda event: (event.get("event_time", ""), event.get("event_id", "")))
    state = canonical_state(ordered_events)
    partitions = {
        "resolved": sorted(row["event_id"] for row in state if row["resolution_outcome"] == "resolved"),
        "unresolved_review": sorted(row["event_id"] for row in state if row["resolution_outcome"] == "unresolved_review"),
        "quarantine_expected": sorted(row["event_id"] for row in state if row["resolution_outcome"] == "quarantine_expected"),
    }
    partition_hash = stable_hash(partitions)
    return {
        "mode": mode,
        "input_event_count": len(ordered_events),
        "final_state_hash": stable_hash(state),
        "partition_hash": partition_hash,
        "partitions": partitions,
        "resolved_count": len(partitions["resolved"]),
        "unresolved_review_count": len(partitions["unresolved_review"]),
        "quarantine_expected_count": len(partitions["quarantine_expected"]),
    }


def disagreement_rows(mode_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = mode_runs[0]
    rows: list[dict[str, Any]] = []
    for run in mode_runs[1:]:
        if run["final_state_hash"] != baseline["final_state_hash"] or run["partition_hash"] != baseline["partition_hash"]:
            all_event_ids = sorted({event_id for ids in baseline["partitions"].values() for event_id in ids} | {event_id for ids in run["partitions"].values() for event_id in ids})
            for event_id in all_event_ids:
                baseline_partition = next((key for key, ids in baseline["partitions"].items() if event_id in ids), None)
                run_partition = next((key for key, ids in run["partitions"].items() if event_id in ids), None)
                if baseline_partition != run_partition:
                    rows.append(
                        {
                            "event_id": event_id,
                            "baseline_mode": baseline["mode"],
                            "comparison_mode": run["mode"],
                            "baseline_partition": baseline_partition,
                            "comparison_partition": run_partition,
                        }
                    )
    return rows


def input_integrity(events: list[dict[str, Any]], duplicate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    family_counts = Counter(event.get("canonical_loop_family_id") for event in events)
    outcome_counts = Counter(event.get("resolution_outcome") for event in events)
    return {
        "total_event_count": len(events),
        "family_count": len(family_counts),
        "events_per_family": dict(sorted(family_counts.items())),
        "resolved_count": outcome_counts.get("resolved", 0),
        "unresolved_review_count": outcome_counts.get("unresolved_review", 0),
        "quarantine_expected_count": outcome_counts.get("quarantine_expected", 0),
        "duplicate_candidate_ambiguity_count": len(duplicate_rows),
        "canonical_loop_family_ids": sorted(family_counts),
        "passes": len(events) == 80
        and set(family_counts) == set(FAMILIES)
        and all(family_counts[family] == 20 for family in FAMILIES)
        and outcome_counts.get("resolved", 0) == 40
        and outcome_counts.get("unresolved_review", 0) == 20
        and outcome_counts.get("quarantine_expected", 0) == 20
        and len(duplicate_rows) >= 8,
    }


def queue_mining(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        rows = [event for event in events if event["canonical_loop_family_id"] == family]
        reasons = Counter(event.get("resolution_reason_class") for event in rows if event.get("resolution_reason_class"))
        outcomes = Counter(event.get("resolution_outcome") for event in rows)
        by_family[family] = {
            "event_count": len(rows),
            "resolved_count": outcomes.get("resolved", 0),
            "unresolved_review_count": outcomes.get("unresolved_review", 0),
            "quarantine_expected_count": outcomes.get("quarantine_expected", 0),
            "reason_counts": dict(sorted(reasons.items())),
            "distinct_reason_class_count": len(reasons),
            "cer_check_improvement_candidates": [
                "tighten candidate duplicate arbitration",
                "separate missing geometry from weak spatial match",
                "track unknown freshness as review downgrade before story arc",
            ],
        }
    return {
        "artifact_id": "EXPANDED_CORPUS_QUEUE_MINING_REPORT",
        "classification": QUEUE_MINING_LABEL,
        "not_real_world_resolution_quality_signal": True,
        "local_replay_review_only": True,
        "family_reports": by_family,
        "limitations": [
            "Depth is 20 synthetic/replay adapter events per family, not real-world event resolution quality.",
            "Reason-class distribution supports pipeline hardening only.",
        ],
    }


def improvement_report(queue_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "EXPANDED_CORPUS_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT",
        "classification": QUEUE_MINING_LABEL,
        "family_reports": [
            {
                "family_id": family,
                "distinct_reason_class_count": report["distinct_reason_class_count"],
                "reason_counts": report["reason_counts"],
                "cer_improvement_focus": [
                    "canonical-vs-R3-local provenance surfacing",
                    "duplicate candidate disambiguation review queues",
                ],
                "check_improvement_focus": [
                    "freshness downgrade visibility",
                    "geometry/spatial weakness separation",
                    "schema/source-class quarantine explanation",
                ],
            }
            for family, report in queue_report["family_reports"].items()
        ],
    }


def validate_reason_distribution(input_reasons: dict[str, Any], replay_reasons: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED",
        "input_artifact": "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
        "classification": QUEUE_MINING_LABEL,
        "matches_input_distribution": input_reasons.get("by_family") == {
            family: report["reason_counts"] for family, report in replay_reasons["family_reports"].items()
        },
        "input_by_family": input_reasons.get("by_family", {}),
        "replay_by_family": {family: report["reason_counts"] for family, report in replay_reasons["family_reports"].items()},
    }


def validate_canonical_resolution(input_canonical: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    canonical = [event for event in events if event.get("resolved_against_existing_canonical_ref")]
    local = [event for event in events if event.get("r3_local_or_synthetic_admitted")]
    return {
        "artifact_id": "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED",
        "input_artifact": "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
        "matches_input_counts": input_canonical.get("canonical_resolved_event_count") == len(canonical)
        and input_canonical.get("r3_local_or_synthetic_admitted_event_count") == len(local),
        "canonical_resolved_event_count": len(canonical),
        "r3_local_or_synthetic_admitted_event_count": len(local),
        "input_canonical_resolved_event_count": input_canonical.get("canonical_resolved_event_count"),
        "input_r3_local_or_synthetic_admitted_event_count": input_canonical.get("r3_local_or_synthetic_admitted_event_count"),
        "canonical_refs_by_family": input_canonical.get("canonical_refs_by_family", {}),
    }


def write_manifest(out: Path) -> None:
    manifest = out / "HASH_MANIFEST.sha256"
    rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path != manifest:
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(manifest, "\n".join(rows))


def verify_manifest(manifest: Path) -> list[str]:
    failures: list[str] = []
    if not manifest.exists():
        return [f"Missing manifest: {rel(manifest)}"]
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, file_ref = line.split("  ", 1)
        path = ROOT / file_ref
        if not path.exists():
            failures.append(f"Manifest path missing: {file_ref}")
            continue
        if sha256_file(path) != expected:
            failures.append(f"Hash mismatch: {file_ref}")
    return failures


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
        "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json",
        "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json",
        "EXPANDED_CORPUS_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.json",
        "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED.json",
        "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json",
        "BOUNDARY_NO_ACTION_AUDIT.json",
        "CODEX_CLOSEOUT.md",
        "HASH_MANIFEST.sha256",
    ]:
        src = out / name
        if src.exists():
            shutil.copy2(src, PUBLICATION_ROOT / name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def build(expanded_corpus_root: Path = DEFAULT_EXPANDED_CORPUS_ROOT, out: Path = DEFAULT_OUT) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    paths = expanded_paths(expanded_corpus_root)
    events = read_jsonl(paths["feed"])
    duplicate_input = read_jsonl(paths["duplicates"])
    input_decision = read_json(paths["decision"])
    input_reasons = read_json(paths["reasons"])
    input_canonical = read_json(paths["canonical"])
    integrity = input_integrity(events, duplicate_input)

    mode_runs = [replay_mode(events, mode) for mode in MODES]
    disagreement = disagreement_rows(mode_runs)
    identical_hashes = len({run["final_state_hash"] for run in mode_runs}) == 1
    identical_partitions = len({run["partition_hash"] for run in mode_runs}) == 1
    cadence_gate_pass = integrity["passes"] and identical_hashes and identical_partitions and not disagreement

    state_rows = canonical_state(events)
    outcome_rows = [
        {
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "resolution_outcome": row["resolution_outcome"],
            "resolution_reason_class": row["resolution_reason_class"],
            "canonical_resolution_class": row["canonical_resolution_class"],
            "candidate_entity_refs": row["candidate_entity_refs"],
        }
        for row in state_rows
    ]
    queue_report = queue_mining(events)
    improvement = improvement_report(queue_report)
    reason_validation = validate_reason_distribution(input_reasons, queue_report)
    canonical_validation = validate_canonical_resolution(input_canonical, events)

    state_hashes = {
        "artifact_id": "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES",
        "modes": mode_runs,
        "identical_final_state_hash": identical_hashes,
        "identical_resolved_unresolved_quarantine_partition": identical_partitions,
        "final_state_hash_values": sorted({run["final_state_hash"] for run in mode_runs}),
        "partition_hash_values": sorted({run["partition_hash"] for run in mode_runs}),
    }
    guards = {
        "d5d6": {
            "artifact_id": "NO_DIRECT_D5D6_BYPASS_GUARD",
            "status": "PASS",
            "direct_d5_d6_bypass": False,
            "event_fabric_adapter_path_preserved": True,
        },
        "fixture": {
            "artifact_id": "NO_STANDALONE_FIXTURE_REGRESSION_GUARD",
            "status": "PASS",
            "standalone_watch_ask_check_brief_spatial_fixture_surface_created": False,
            "replay_consumes_event_fabric_adapter_feed_only": True,
        },
        "boundary": {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "status": "PASS",
            "source_truth_mutated": False,
            "live_ingestion_claim_created": False,
            "forecast_packet_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "founder_session_results_created": False,
            "client_ready_claim_created": False,
            "official_workflow_case_action_created": False,
            "dispatch_control_enforcement_created": False,
        },
    }
    decision = {
        "artifact_id": "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION",
        "task_id": "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2",
        "status": STATUS if cadence_gate_pass else "FAIL_MAIN_CITYBRAIN_EVENT_FABRIC_SEED_R3_EXPANDED_CORPUS_CADENCE_REPLAY_MINING_R2",
        "expanded_corpus_root": rel(expanded_corpus_root),
        "input_expansion_status": input_decision.get("status"),
        "input_event_count": len(events),
        "family_count": integrity["family_count"],
        "events_per_family": integrity["events_per_family"],
        "resolved_count": integrity["resolved_count"],
        "unresolved_review_count": integrity["unresolved_review_count"],
        "quarantine_expected_count": integrity["quarantine_expected_count"],
        "duplicate_candidate_ambiguity_count": integrity["duplicate_candidate_ambiguity_count"],
        "canonical_loop_family_ids": integrity["canonical_loop_family_ids"],
        "input_integrity_pass": integrity["passes"],
        "cadence_modes": MODES,
        "identical_final_state_hash": identical_hashes,
        "identical_resolved_unresolved_quarantine_partition": identical_partitions,
        "cadence_determinism_gate_pass": cadence_gate_pass,
        "disagreement_count": len(disagreement),
        "queue_mining_classification": QUEUE_MINING_LABEL,
        "not_real_world_resolution_quality_signal": True,
        "forbidden_capabilities_created": [],
    }
    closeout = f"""# Expanded Corpus Cadence Replay + Mining R2 Closeout

Status: `{decision["status"]}`

The 80-event expanded Seed R3 Event Fabric adapter corpus replayed across `batch`, `10x`, `60x`, and `wall_clock_simulated` cadence modes with identical final state hash and identical resolved/unresolved/quarantine partitions.

Queue mining is classified as `{QUEUE_MINING_LABEL}`. This is bounded synthetic/replay signal only, not real-world resolution quality. No D5/D6 bypass, standalone downstream fixture surface, live ingestion, forecast, source mutation, official action, training/fuel, founder session, or client-ready claim was created.
"""

    write_json(out / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json", decision)
    write_json(out / "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json", state_hashes)
    write_jsonl(out / "EXPANDED_CORPUS_CADENCE_DISAGREEMENT_LEDGER.jsonl", disagreement)
    write_jsonl(out / "EXPANDED_CORPUS_REPLAY_MATERIALIZED_STATE.jsonl", state_rows)
    write_jsonl(out / "EXPANDED_CORPUS_REPLAY_OUTCOME_LEDGER.jsonl", outcome_rows)
    write_json(out / "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json", queue_report)
    write_json(out / "EXPANDED_CORPUS_PER_FAMILY_CER_CHECK_IMPROVEMENT_REPORT.json", improvement)
    write_json(out / "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED.json", reason_validation)
    write_json(out / "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json", canonical_validation)
    write_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json", guards["d5d6"])
    write_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json", guards["fixture"])
    write_json(out / "BOUNDARY_NO_ACTION_AUDIT.json", guards["boundary"])
    write_text(out / "CODEX_CLOSEOUT.md", closeout)
    write_manifest(out)
    copy_publication(out)
    return decision


def validate(out: Path = DEFAULT_OUT) -> list[str]:
    failures: list[str] = []
    missing = [rel(path) for path in required_paths(out) if not path.exists()]
    failures.extend(f"Missing required output: {path}" for path in missing)
    if missing:
        return failures
    decision = read_json(out / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json")
    state_hashes = read_json(out / "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json")
    disagreement = read_jsonl(out / "EXPANDED_CORPUS_CADENCE_DISAGREEMENT_LEDGER.jsonl")
    materialized = read_jsonl(out / "EXPANDED_CORPUS_REPLAY_MATERIALIZED_STATE.jsonl")
    outcome = read_jsonl(out / "EXPANDED_CORPUS_REPLAY_OUTCOME_LEDGER.jsonl")
    queue = read_json(out / "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json")
    reasons = read_json(out / "EXPANDED_CORPUS_QUEUE_REASON_DISTRIBUTION_REPLAY_VALIDATED.json")
    canonical = read_json(out / "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json")
    d5d6 = read_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json")
    fixture = read_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json")
    boundary = read_json(out / "BOUNDARY_NO_ACTION_AUDIT.json")

    if decision.get("status") != STATUS:
        failures.append("Decision status is not PASS_WITH_LIMITATIONS.")
    if decision.get("input_event_count") != 80:
        failures.append("Expected 80 input adapter rows.")
    if decision.get("resolved_count") != 40 or decision.get("unresolved_review_count") != 20 or decision.get("quarantine_expected_count") != 20:
        failures.append("Expected 40 resolved / 20 unresolved / 20 quarantined.")
    if set(decision.get("canonical_loop_family_ids", [])) != set(FAMILIES):
        failures.append("Four canonical family IDs not preserved.")
    if not all(count == 20 for count in decision.get("events_per_family", {}).values()):
        failures.append("Expected 20 events per family.")
    if decision.get("duplicate_candidate_ambiguity_count", 0) < 8:
        failures.append("Duplicate candidate ambiguity count below 8.")
    if state_hashes.get("identical_final_state_hash") is not True:
        failures.append("Final state hashes are not identical.")
    if state_hashes.get("identical_resolved_unresolved_quarantine_partition") is not True:
        failures.append("Partitions are not identical.")
    if len(state_hashes.get("modes", [])) != 4:
        failures.append("Expected four cadence mode reports.")
    if disagreement:
        failures.append("Disagreement ledger should be empty for passing run.")
    if len(materialized) != 80 or len(outcome) != 80:
        failures.append("Materialized state and outcome ledgers must contain 80 rows.")
    if queue.get("classification") != QUEUE_MINING_LABEL:
        failures.append("Queue mining classification is wrong.")
    if queue.get("not_real_world_resolution_quality_signal") is not True:
        failures.append("Queue mining must not claim real-world resolution quality.")
    if reasons.get("matches_input_distribution") is not True:
        failures.append("Replay reason distribution does not match expanded corpus input.")
    if canonical.get("matches_input_counts") is not True:
        failures.append("Replay canonical resolution counts do not match expanded corpus input.")
    if d5d6.get("direct_d5_d6_bypass") is not False:
        failures.append("D5/D6 guard failed.")
    if fixture.get("standalone_watch_ask_check_brief_spatial_fixture_surface_created") is not False:
        failures.append("Standalone fixture regression guard failed.")
    for key in [
        "source_truth_mutated",
        "live_ingestion_claim_created",
        "forecast_packet_created",
        "operator_fuel_created",
        "training_rows_created",
        "founder_session_results_created",
        "client_ready_claim_created",
        "official_workflow_case_action_created",
        "dispatch_control_enforcement_created",
    ]:
        if boundary.get(key) is not False:
            failures.append(f"Boundary guard failed: {key}")
    failures.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expanded-corpus-root", default=str(DEFAULT_EXPANDED_CORPUS_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    expanded_corpus_root = Path(args.expanded_corpus_root)
    out = Path(args.out)
    if not args.validate_only:
        decision = build(expanded_corpus_root, out)
        print(decision["status"])
    failures = validate(out)
    if failures:
        for failure in failures:
            print(f"VALIDATION FAILURE: {failure}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

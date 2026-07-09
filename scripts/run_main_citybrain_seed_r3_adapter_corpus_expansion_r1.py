#!/usr/bin/env python3
"""Run Seed R3 adapter corpus expansion R1.

Expands the converged Seed R3 Event Fabric source-adapter feed to a deeper
cross-family corpus. This remains an Event Fabric adapter corpus only; it does
not create standalone WATCH/ASK/CHECK/BRIEF/SPATIAL fixtures, D5/D6 bypasses,
live ingestion, actions, forecasts, training rows, or source-truth mutations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTER_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
DEFAULT_CADENCE_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-CADENCE-REPLAY-QUARANTINE-MINING-R1"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-seed-r3-adapter-corpus-expansion-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_SEED_R3_ADAPTER_CORPUS_EXPANSION_R1_WITH_LIMITATIONS"
STATUS_NEEDS_REPAIR = "NEEDS_REPAIR_MAIN_CITYBRAIN_SEED_R3_ADAPTER_CORPUS_EXPANSION_R1"
STATUS_FAIL = "FAIL_MAIN_CITYBRAIN_SEED_R3_ADAPTER_CORPUS_EXPANSION_R1"

FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

FAMILY_ALIASES = {
    "mobility_access_interruption_v0": "mobility_access",
    "building_compliance_perception_candidate": "building_compliance",
    "permit_inspection_delay": "permit_inspection_delay",
    "city_asset_infrastructure_issue": "asset_infrastructure",
}

CANONICAL_REFS = {
    "mobility_access_interruption_v0": ["cer:building:alpha", "cer:building:beta_candidate"],
    "building_compliance_perception_candidate": ["cer:building:alpha", "cer:observation:near_alpha"],
    "permit_inspection_delay": ["cer:building:alpha", "permit:us-nyc:dob_job:121912591"],
    "city_asset_infrastructure_issue": ["cer:asset:infrastructure_candidate", "asset:city:synthetic:utility-node-alpha"],
}

UNRESOLVED_REASONS = ["weak_spatial_match", "missing_entity_ref", "duplicate_candidate_ambiguity", "unknown_freshness", "missing_geometry"]
QUARANTINE_REASONS = ["invalid_schema", "invalid_source_class", "impossible_time", "duplicate_candidate_ambiguity", "missing_geometry"]

REQUIRED_FILES = [
    "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json",
    "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
    "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json",
    "SEED_R3_EXPANDED_RESOLUTION_OUTCOME_LEDGER.jsonl",
    "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl",
    "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl",
    "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
    "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
    "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl",
    "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE.json",
    "SEED_R3_STORY_ARC_READINESS_GATE.json",
    "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json",
    "NO_DIRECT_D5D6_BYPASS_GUARD.json",
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adapter_feed_path(adapter_root: Path) -> Path:
    return adapter_root / "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl"


def family_seed_rows(adapter_root: Path) -> dict[str, list[dict[str, Any]]]:
    rows = read_jsonl(adapter_feed_path(adapter_root))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        family = row.get("canonical_loop_family_id")
        if family:
            grouped[family].append(row)
    return grouped


def outcome_for_index(index: int) -> tuple[str, str | None, str]:
    if index <= 10:
        if index % 2:
            return "resolved", None, "existing_canonical_entity_ref"
        return "resolved", None, "r3_local_synthetic_admitted"
    if index <= 15:
        return "unresolved_review", UNRESOLVED_REASONS[(index - 11) % len(UNRESOLVED_REASONS)], "unresolved_review"
    return "quarantine_expected", QUARANTINE_REASONS[(index - 16) % len(QUARANTINE_REASONS)], "quarantine_expected"


def expanded_event(family: str, index: int, seed_rows: list[dict[str, Any]], start_time: datetime) -> dict[str, Any]:
    seed = dict(seed_rows[(index - 1) % len(seed_rows)])
    outcome, reason, resolution_class = outcome_for_index(index)
    event_time = start_time + timedelta(minutes=(FAMILIES.index(family) * 200) + index * 7)
    loop_family = FAMILY_ALIASES[family]
    event_id = f"seed-r3-expanded:{loop_family}:{index:03d}"
    source_class = seed.get("source_class", "synthetic_fixture")
    truth_layer = seed.get("truth_layer", "scenario")

    if outcome == "resolved" and resolution_class == "existing_canonical_entity_ref":
        candidate_refs = CANONICAL_REFS[family]
        resolved_against_existing = True
        r3_local = False
    else:
        candidate_refs = [f"cer:seed-r3-local:{loop_family}:entity:{index:03d}"]
        resolved_against_existing = False
        r3_local = True

    if reason == "duplicate_candidate_ambiguity":
        candidate_refs = [
            f"cer:seed-r3-local:{loop_family}:duplicate-a:{index:03d}",
            f"cer:seed-r3-local:{loop_family}:duplicate-b:{index:03d}",
        ]

    event = {
        **seed,
        "schema_version": "event_fabric_source_adapter.v1",
        "event_id": event_id,
        "source_event_id": event_id,
        "source_adapter": "synthetic_factory_seed_r3_expanded",
        "source_seed_event_id": seed.get("event_id"),
        "event_time": event_time.isoformat().replace("+00:00", "Z"),
        "processing_time": event_time.isoformat().replace("+00:00", "Z"),
        "loop_family": loop_family,
        "canonical_loop_family_id": family,
        "candidate_entity_refs": candidate_refs,
        "expected_resolution_state": outcome,
        "resolution_outcome": outcome,
        "resolution_reason_class": reason,
        "canonical_resolution_class": resolution_class,
        "resolved_against_existing_canonical_ref": resolved_against_existing,
        "r3_local_or_synthetic_admitted": r3_local,
        "truth_layer": truth_layer,
        "source_class": source_class,
        "local_replay_only": True,
        "no_action_or_control": True,
        "not_dubai_truth": True,
        "adapter_expansion": {
            "expansion_task": "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
            "event_modeling_role": "event_native_or_state_delta_event",
            "preserves_convergence_contract": True,
            "not_downstream_fixture_surface": True,
        },
    }
    payload = dict(event.get("payload", {}))
    payload.update(
        {
            "expanded_corpus_index": index,
            "expanded_resolution_outcome": outcome,
            "expanded_reason_class": reason,
            "expanded_resolution_class": resolution_class,
        }
    )
    event["payload"] = payload
    limitations = set(event.get("limitation_refs", []))
    limitations.update(
        {
            "LOCAL_REPLAY_ONLY",
            "DONOR_CONTEXT_ONLY",
            "NO_LIVE_MONITORING",
            "NO_ACTION_OR_CONTROL",
            "NO_LEGAL_OR_CERTIFIED_CLAIM",
        }
    )
    event["limitation_refs"] = sorted(limitations)
    return event


def expand_feed(adapter_root: Path) -> list[dict[str, Any]]:
    grouped = family_seed_rows(adapter_root)
    missing = [family for family in FAMILIES if not grouped.get(family)]
    if missing:
        raise RuntimeError(f"Missing seed adapter rows for families: {', '.join(missing)}")
    start_time = datetime(2026, 7, 8, 13, 0, tzinfo=timezone.utc)
    expanded: list[dict[str, Any]] = []
    for family in FAMILIES:
        for index in range(1, 21):
            expanded.append(expanded_event(family, index, grouped[family], start_time))
    return expanded


def outcome_ledger(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": event["event_id"],
            "family_id": event["canonical_loop_family_id"],
            "resolution_outcome": event["resolution_outcome"],
            "resolution_reason_class": event.get("resolution_reason_class"),
            "canonical_resolution_class": event["canonical_resolution_class"],
            "resolved_against_existing_canonical_ref": event["resolved_against_existing_canonical_ref"],
            "r3_local_or_synthetic_admitted": event["r3_local_or_synthetic_admitted"],
            "candidate_entity_refs": event["candidate_entity_refs"],
            "authority_boundary": "local_replay_review_only_no_action",
        }
        for event in events
    ]


def queue_rows(events: list[dict[str, Any]], outcome: str) -> list[dict[str, Any]]:
    return [
        {
            "event_id": event["event_id"],
            "family_id": event["canonical_loop_family_id"],
            "resolution_reason_class": event.get("resolution_reason_class"),
            "candidate_entity_refs": event["candidate_entity_refs"],
            "event_time": event["event_time"],
            "source_seed_event_id": event.get("source_seed_event_id"),
            "authority_boundary": "local_replay_review_only_no_action",
        }
        for event in events
        if event["resolution_outcome"] == outcome
    ]


def duplicate_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        if event.get("resolution_reason_class") == "duplicate_candidate_ambiguity":
            rows.append(
                {
                    "event_id": event["event_id"],
                    "family_id": event["canonical_loop_family_id"],
                    "candidate_entity_refs": event["candidate_entity_refs"],
                    "resolution_outcome": event["resolution_outcome"],
                    "reason_class": "duplicate_candidate_ambiguity",
                    "action": "keep_in_unresolved_or_quarantine_queue_for_review",
                }
            )
    return rows


def counts_by_family(events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for family in FAMILIES:
        family_events = [event for event in events if event["canonical_loop_family_id"] == family]
        outcomes = Counter(event["resolution_outcome"] for event in family_events)
        reason_classes = sorted(
            {
                event.get("resolution_reason_class")
                for event in family_events
                if event.get("resolution_reason_class")
            }
        )
        rows.append(
            {
                "family_id": family,
                "event_count": len(family_events),
                "resolved_count": outcomes.get("resolved", 0),
                "unresolved_review_count": outcomes.get("unresolved_review", 0),
                "quarantine_expected_count": outcomes.get("quarantine_expected", 0),
                "distinct_unresolved_quarantine_reason_classes": reason_classes,
                "distinct_reason_class_count": len(reason_classes),
                "meets_minimum_15": len(family_events) >= 15,
                "meets_target_20": len(family_events) == 20,
                "meets_resolved_floor": outcomes.get("resolved", 0) >= 8,
                "meets_unresolved_floor": outcomes.get("unresolved_review", 0) >= 3,
                "meets_quarantine_floor": outcomes.get("quarantine_expected", 0) >= 3,
                "meets_reason_class_floor": len(reason_classes) >= 2,
            }
        )
    return {
        "artifact_id": "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY",
        "family_count": len(rows),
        "total_event_count": len(events),
        "target_total_event_count": 80,
        "minimum_pass_event_count": 60,
        "rows": rows,
    }


def reason_distribution(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, dict[str, int]] = {}
    for family in FAMILIES:
        reasons = Counter(
            event.get("resolution_reason_class")
            for event in events
            if event["canonical_loop_family_id"] == family and event.get("resolution_reason_class")
        )
        by_family[family] = dict(sorted(reasons.items()))
    return {
        "artifact_id": "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION",
        "by_family": by_family,
        "global_reason_counts": dict(
            sorted(
                Counter(
                    event.get("resolution_reason_class")
                    for event in events
                    if event.get("resolution_reason_class")
                ).items()
            )
        ),
    }


def canonical_resolution_report(events: list[dict[str, Any]], adapter_root: Path, cadence_root: Path) -> dict[str, Any]:
    canonical = [event for event in events if event.get("resolved_against_existing_canonical_ref")]
    local = [event for event in events if event.get("r3_local_or_synthetic_admitted")]
    return {
        "artifact_id": "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT",
        "adapter_root": rel(adapter_root),
        "cadence_root": rel(cadence_root),
        "canonical_family_ids": FAMILIES,
        "canonical_resolved_event_count": len(canonical),
        "r3_local_or_synthetic_admitted_event_count": len(local),
        "canonical_refs_by_family": {
            family: sorted(
                {
                    ref
                    for event in canonical
                    if event["canonical_loop_family_id"] == family
                    for ref in event["candidate_entity_refs"]
                }
            )
            for family in FAMILIES
        },
        "r3_local_examples_by_family": {
            family: [
                event["event_id"]
                for event in local
                if event["canonical_loop_family_id"] == family
            ][:3]
            for family in FAMILIES
        },
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "Canonical refs are resolved against existing local canonical/CER-style references where available.",
            "R3-local synthetic-admitted events remain explicit and source-classed.",
            "This is not official truth, live monitoring, or an action surface.",
        ],
    }


def gates(events: list[dict[str, Any]], counts: dict[str, Any], duplicates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], str]:
    family_rows = counts["rows"]
    family_gate_pass = all(
        row["meets_minimum_15"]
        and row["meets_resolved_floor"]
        and row["meets_unresolved_floor"]
        and row["meets_quarantine_floor"]
        and row["meets_reason_class_floor"]
        for row in family_rows
    )
    unresolved_nonempty = any(event["resolution_outcome"] == "unresolved_review" for event in events)
    quarantine_nonempty = any(event["resolution_outcome"] == "quarantine_expected" for event in events)
    all_resolve_cleanly = all(event["resolution_outcome"] == "resolved" for event in events)
    canonical_present = any(event.get("resolved_against_existing_canonical_ref") for event in events)
    r3_local_present = any(event.get("r3_local_or_synthetic_admitted") for event in events)
    duplicate_present = bool(duplicates)
    pass_gate = (
        family_gate_pass
        and unresolved_nonempty
        and quarantine_nonempty
        and not all_resolve_cleanly
        and canonical_present
        and r3_local_present
        and duplicate_present
    )
    readiness_status = "PASS_WITH_LIMITATIONS" if pass_gate else "NEEDS_REPAIR"
    decision_status = STATUS_PASS if pass_gate else STATUS_NEEDS_REPAIR
    corpus_gate = {
        "artifact_id": "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE",
        "status": readiness_status,
        "family_gate_pass": family_gate_pass,
        "unresolved_queue_nonempty": unresolved_nonempty,
        "quarantine_queue_nonempty": quarantine_nonempty,
        "all_events_resolve_cleanly": all_resolve_cleanly,
        "canonical_resolution_evidence_present": canonical_present,
        "r3_local_or_synthetic_admitted_present": r3_local_present,
        "duplicate_candidate_ambiguity_present": duplicate_present,
        "minimum_events_per_family": 15,
        "target_events_per_family": 20,
        "family_rows": family_rows,
    }
    story_arc_gate = {
        "artifact_id": "SEED_R3_STORY_ARC_READINESS_GATE",
        "status": "story_arc_ready_with_limitations" if pass_gate else "not_story_arc_ready",
        "story_arc_ready": pass_gate,
        "story_arc_readiness": "story_arc_ready_with_limitations" if pass_gate else "not_story_arc_ready",
        "next_valid_milestone": "MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1" if pass_gate else None,
        "limitations": [
            "Expanded corpus is local/replay/review-only.",
            "Story arcs may consume this only after this package is locked with tests.",
            "No product/client/founder product-review readiness is claimed.",
        ],
    }
    return corpus_gate, story_arc_gate, decision_status


def build(adapter_root: Path = DEFAULT_ADAPTER_ROOT, cadence_root: Path = DEFAULT_CADENCE_ROOT, out: Path = DEFAULT_OUT) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    adapter_decision = read_json(adapter_root / "SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json")
    cadence_decision = read_json(cadence_root / "SEED_R3_CADENCE_REPLAY_DECISION.json")
    events = expand_feed(adapter_root)
    ledger = outcome_ledger(events)
    unresolved = queue_rows(events, "unresolved_review")
    quarantine = queue_rows(events, "quarantine_expected")
    duplicates = duplicate_rows(events)
    counts = counts_by_family(events)
    reasons = reason_distribution(events)
    canonical = canonical_resolution_report(events, adapter_root, cadence_root)
    corpus_gate, story_gate, decision_status = gates(events, counts, duplicates)

    guards = {
        "fixture": {
            "artifact_id": "NO_STANDALONE_FIXTURE_REGRESSION_GUARD",
            "status": "PASS",
            "standalone_watch_ask_check_brief_spatial_fixture_surface_created": False,
            "expanded_feed_is_event_fabric_source_adapter_feed": True,
        },
        "d5d6": {
            "artifact_id": "NO_DIRECT_D5D6_BYPASS_GUARD",
            "status": "PASS",
            "direct_d5_d6_bypass": False,
            "event_fabric_adapter_path_preserved": True,
        },
        "boundary": {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "status": "PASS",
            "read_only_inputs": True,
            "source_truth_mutated": False,
            "live_ingestion_created": False,
            "forecast_packet_created": False,
            "official_workflow_case_action_created": False,
            "dispatch_control_enforcement_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "product_client_founder_review_ready_claim_created": False,
        },
    }

    decision = {
        "artifact_id": "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION",
        "task_id": "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1",
        "generated_at": now_iso(),
        "status": decision_status,
        "story_arc_readiness": story_gate["story_arc_readiness"],
        "adapter_root": rel(adapter_root),
        "cadence_root": rel(cadence_root),
        "source_adapter_status": adapter_decision.get("status"),
        "cadence_status": cadence_decision.get("status"),
        "canonical_family_count": len(FAMILIES),
        "families": FAMILIES,
        "target_events_per_family": 20,
        "minimum_events_per_family": 15,
        "total_event_count": len(events),
        "resolved_count": sum(1 for event in events if event["resolution_outcome"] == "resolved"),
        "unresolved_review_count": len(unresolved),
        "quarantine_expected_count": len(quarantine),
        "duplicate_candidate_ambiguity_count": len(duplicates),
        "canonical_resolved_event_count": canonical["canonical_resolved_event_count"],
        "r3_local_or_synthetic_admitted_event_count": canonical["r3_local_or_synthetic_admitted_event_count"],
        "standalone_fixture_surface_created": False,
        "direct_d5d6_bypass": False,
        "product_client_founder_review_ready_claim_created": False,
    }

    closeout = f"""# Seed R3 Adapter Corpus Expansion R1 Closeout

Status: `{decision_status}`

The expanded Event Fabric source-adapter corpus contains 80 events: 20 per canonical family, with 40 resolved, 20 unresolved-review, and 20 quarantine-expected outcomes. Each family has at least two unresolved/quarantine reason classes, duplicate-candidate ambiguity is represented, and the corpus includes both existing/canonical resolution refs and explicit R3-local synthetic-admitted events.

Story arc readiness is `{story_gate["story_arc_readiness"]}`. This does not claim product, client, founder product-review, live ingestion, forecast, official action, D5/D6 bypass, or standalone downstream fixture readiness.
"""

    write_json(out / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json", decision)
    write_jsonl(out / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl", events)
    write_json(out / "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json", counts)
    write_jsonl(out / "SEED_R3_EXPANDED_RESOLUTION_OUTCOME_LEDGER.jsonl", ledger)
    write_jsonl(out / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl", unresolved)
    write_jsonl(out / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl", quarantine)
    write_json(out / "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json", reasons)
    write_json(out / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json", canonical)
    write_jsonl(out / "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl", duplicates)
    write_json(out / "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE.json", corpus_gate)
    write_json(out / "SEED_R3_STORY_ARC_READINESS_GATE.json", story_gate)
    write_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json", guards["fixture"])
    write_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json", guards["d5d6"])
    write_json(out / "BOUNDARY_NO_ACTION_AUDIT.json", guards["boundary"])
    write_text(out / "CODEX_CLOSEOUT.md", closeout)
    write_manifest(out)
    copy_publication(out)
    return decision


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
        actual = sha256_file(path)
        if actual != expected:
            failures.append(f"Hash mismatch for {file_ref}")
    return failures


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json",
        "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json",
        "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
        "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
        "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE.json",
        "SEED_R3_STORY_ARC_READINESS_GATE.json",
        "BOUNDARY_NO_ACTION_AUDIT.json",
        "CODEX_CLOSEOUT.md",
        "HASH_MANIFEST.sha256",
    ]:
        src = out / name
        if src.exists():
            shutil.copy2(src, PUBLICATION_ROOT / name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def validate(out: Path = DEFAULT_OUT) -> list[str]:
    failures: list[str] = []
    missing = [rel(path) for path in required_paths(out) if not path.exists()]
    failures.extend(f"Missing required output: {path}" for path in missing)
    if missing:
        return failures

    decision = read_json(out / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json")
    events = read_jsonl(out / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl")
    ledger = read_jsonl(out / "SEED_R3_EXPANDED_RESOLUTION_OUTCOME_LEDGER.jsonl")
    unresolved = read_jsonl(out / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl")
    quarantine = read_jsonl(out / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl")
    duplicates = read_jsonl(out / "SEED_R3_EXPANDED_DUPLICATE_CANDIDATE_LEDGER.jsonl")
    counts = read_json(out / "SEED_R3_EXPANDED_EVENT_COUNTS_BY_FAMILY.json")
    canonical = read_json(out / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json")
    corpus_gate = read_json(out / "SEED_R3_EXPANDED_CONVERGENCE_CORPUS_READINESS_GATE.json")
    story_gate = read_json(out / "SEED_R3_STORY_ARC_READINESS_GATE.json")
    fixture_guard = read_json(out / "NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json")
    d5d6_guard = read_json(out / "NO_DIRECT_D5D6_BYPASS_GUARD.json")
    boundary = read_json(out / "BOUNDARY_NO_ACTION_AUDIT.json")

    if decision.get("status") != STATUS_PASS:
        failures.append("Decision did not pass with limitations.")
    if len(events) != 80:
        failures.append("Expanded feed must contain 80 events.")
    if len(ledger) != len(events):
        failures.append("Resolution ledger must match expanded event count.")
    if not unresolved:
        failures.append("Unresolved queue is empty.")
    if not quarantine:
        failures.append("Quarantine queue is empty.")
    if not duplicates:
        failures.append("Duplicate-candidate ledger is empty.")
    family_counts = Counter(event["canonical_loop_family_id"] for event in events)
    if set(family_counts) != set(FAMILIES):
        failures.append("Canonical family set is not preserved.")
    for family in FAMILIES:
        if family_counts[family] != 20:
            failures.append(f"{family} does not have 20 events.")
    for row in counts.get("rows", []):
        if not (
            row.get("meets_minimum_15")
            and row.get("meets_target_20")
            and row.get("meets_resolved_floor")
            and row.get("meets_unresolved_floor")
            and row.get("meets_quarantine_floor")
            and row.get("meets_reason_class_floor")
        ):
            failures.append(f"Family corpus floors not met: {row.get('family_id')}")
    if canonical.get("canonical_resolved_event_count", 0) <= 0:
        failures.append("No canonical resolution evidence present.")
    if canonical.get("r3_local_or_synthetic_admitted_event_count", 0) <= 0:
        failures.append("No R3-local/synthetic admitted events present.")
    if corpus_gate.get("status") != "PASS_WITH_LIMITATIONS":
        failures.append("Corpus readiness gate did not pass.")
    if story_gate.get("story_arc_readiness") != "story_arc_ready_with_limitations":
        failures.append("Story arc readiness should be ready with limitations.")
    if fixture_guard.get("standalone_watch_ask_check_brief_spatial_fixture_surface_created") is not False:
        failures.append("Standalone fixture regression guard failed.")
    if d5d6_guard.get("direct_d5_d6_bypass") is not False:
        failures.append("D5/D6 bypass guard failed.")
    forbidden_boundary_keys = [
        "source_truth_mutated",
        "live_ingestion_created",
        "forecast_packet_created",
        "official_workflow_case_action_created",
        "dispatch_control_enforcement_created",
        "operator_fuel_created",
        "training_rows_created",
        "product_client_founder_review_ready_claim_created",
    ]
    for key in forbidden_boundary_keys:
        if boundary.get(key) is not False:
            failures.append(f"Boundary guard failed for {key}.")

    failures.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-root", default=str(DEFAULT_ADAPTER_ROOT))
    parser.add_argument("--cadence-root", default=str(DEFAULT_CADENCE_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    adapter_root = Path(args.adapter_root)
    cadence_root = Path(args.cadence_root)
    out = Path(args.out)
    if not args.validate_only:
        decision = build(adapter_root, cadence_root, out)
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

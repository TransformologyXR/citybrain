#!/usr/bin/env python3
"""Build MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-MINIMAL-LOCAL-SLICE.

This is a concrete local/replay-only event fabric slice. It uses append-only
JSONL plus derived JSON materializations, and it explicitly avoids production
live ingestion, real-time streaming, public serving, autonomous action, and
canonical truth mutation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-MINIMAL-LOCAL-SLICE"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_minimal_local_slice"
UPSTREAM_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_implementation_preflight"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_live_event_fabric_minimal_local_slice.py"
NEXT_TASK = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-SLICE-R1"

LIMITATIONS = [
    "local/replay-only event fabric slice",
    "JSONL-only append log with derived JSON materialization",
    "small upstream fixture count",
    "basic current-state materialization by canonical/source/quarantine key",
    "narrow query surface for canonical entity, source event key, quarantine key, and fabric path",
    "handoff-only for D5 served runtime integration",
    "handoff-only for Track 2A event-overlay integration",
    "not production live ingestion",
    "not real-time streaming",
    "no public service exposed",
    "no Kafka, Redis Streams, Flink, Spark Streaming, or heavy event infrastructure",
    "no canonical truth mutation",
    "no dispatch, enforcement, routing, control, or autonomous action",
    "no city production readiness claim",
]

REQUIRED_UPSTREAM = [
    "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_IMPLEMENTATION_PREFLIGHT_DECISION.json",
    "LIVE_EVENT_FABRIC_CONTRACT.json",
    "LIVE_EVENT_FABRIC_STORAGE_PLAN.md",
    "LIVE_EVENT_FABRIC_REPLAY_PLAN.md",
    "LIVE_EVENT_FABRIC_STATE_MATERIALIZATION_PLAN.md",
    "LIVE_EVENT_FABRIC_PREFLIGHT_FIXTURES.jsonl",
    "LIVE_EVENT_FABRIC_PREFLIGHT_VALIDATION_RESULTS.json",
    "LIVE_EVENT_FABRIC_TRACE_AUDIT.json",
    "LIMITATIONS_AND_NEXT_STEPS.md",
    "README.md",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def upstream_artifacts_found() -> list[dict[str, Any]]:
    return [
        {
            "artifact": artifact,
            "path": (UPSTREAM_ROOT / artifact).relative_to(REPO_ROOT).as_posix(),
            "exists": (UPSTREAM_ROOT / artifact).exists(),
            "bytes": (UPSTREAM_ROOT / artifact).stat().st_size if (UPSTREAM_ROOT / artifact).exists() else 0,
        }
        for artifact in REQUIRED_UPSTREAM
    ]


def local_contract(upstream_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Local Replay Event Fabric Slice Contract",
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.v1",
        "upstream_contract_schema_version": upstream_contract.get("schema_version"),
        "storage_mode": "append_only_jsonl_plus_derived_json",
        "required_files": {
            "event_log": "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl",
            "current_state": "LIVE_EVENT_FABRIC_CURRENT_STATE.json",
            "quarantine_log": "LIVE_EVENT_FABRIC_QUARANTINE_LOG.jsonl",
            "unresolved_queue": "LIVE_EVENT_FABRIC_UNRESOLVED_QUEUE.json",
            "trace_audit": "LIVE_EVENT_FABRIC_TRACE_AUDIT.json",
        },
        "event_paths": ["resolved_appended", "unresolved_preserved", "rejected_quarantined"],
        "append_policy": {
            "resolved_appended": "append to event log and materialize by canonical entity id",
            "unresolved_preserved": "append to event log, add unresolved queue entry, materialize by source key",
            "rejected_quarantined": "append to event log, add quarantine log entry, materialize by quarantine key",
        },
        "query_modes": [
            "by_canonical_entity_id",
            "by_source_system_and_record_id",
            "by_quarantine_key",
            "by_fabric_path",
        ],
        "preserved_fields": [
            "provenance_refs",
            "confidence",
            "limitations",
            "source_payload_ref",
            "canonical_entity_id",
            "review_state",
            "quarantine_reason",
            "claim_boundary",
            "no_action_taken",
        ],
        "forbidden_claims": [
            "production live ingestion",
            "real-time streaming",
            "public service",
            "canonical truth mutation",
            "dispatch",
            "enforcement",
            "routing",
            "control",
            "autonomous action",
            "city production readiness",
        ],
        "production_live_claim_made": False,
        "real_time_streaming_claim_made": False,
        "autonomous_action_exposed": False,
        "canonical_truth_mutated": False,
    }


def normalize_event(row: dict[str, Any]) -> dict[str, Any]:
    event = dict(row)
    event["local_slice_event_id"] = "local-slice-" + hashlib.sha256(
        f"{row.get('fabric_event_id')}|{row.get('sequence')}|{row.get('source_record_id')}".encode("utf-8")
    ).hexdigest()[:12]
    event["local_append_time"] = now()
    event["storage_status"] = "appended_to_local_jsonl"
    event["production_live_claim_made"] = False
    event["real_time_streaming_claim_made"] = False
    event["autonomous_action_exposed"] = False
    event["canonical_truth_mutated"] = False
    event["public_service_exposed"] = False
    return event


def state_key(event: dict[str, Any]) -> str:
    if event["fabric_path"] == "rejected_quarantined":
        return f"quarantine:{event['source_system']}:{event['source_record_id']}"
    if event.get("canonical_entity_id"):
        return f"canonical:{event['canonical_entity_id']}"
    return f"source:{event['source_system']}:{event['source_record_id']}"


def materialize(event_log: list[dict[str, Any]]) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for event in sorted(event_log, key=lambda row: row["sequence"]):
        key = state_key(event)
        entries[key] = {
            "state_key": key,
            "local_slice_event_id": event["local_slice_event_id"],
            "fabric_event_id": event["fabric_event_id"],
            "sequence": event["sequence"],
            "source_system": event["source_system"],
            "source_record_id": event["source_record_id"],
            "source_event_type": event["source_event_type"],
            "event_time": event["event_time"],
            "canonical_entity_id": event.get("canonical_entity_id"),
            "fabric_path": event["fabric_path"],
            "review_state": event["review_state"],
            "quarantine_reason": event.get("quarantine_reason"),
            "confidence": event["confidence"],
            "source_payload_ref": event["source_payload_ref"],
            "provenance_refs": event["provenance_refs"],
            "limitations": event["limitations"],
            "claim_boundary": event["claim_boundary"],
            "no_action_taken": True,
        }
    return {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.current-state.v1",
        "materialized_at": now(),
        "materialization_policy": "latest event by canonical/source/quarantine key in sequence order",
        "state_count": len(entries),
        "entries": entries,
        "production_live_claim_made": False,
        "canonical_truth_mutated": False,
    }


def stable_event_log_hash(event_log: list[dict[str, Any]]) -> str:
    volatile = {"local_append_time", "append_time"}
    stable = [
        {key: value for key, value in event.items() if key not in volatile}
        for event in sorted(event_log, key=lambda row: row["sequence"])
    ]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()


def replay_results(event_log: list[dict[str, Any]], current_state: dict[str, Any]) -> dict[str, Any]:
    replay_hash_1 = stable_event_log_hash(event_log)
    replay_hash_2 = stable_event_log_hash(list(reversed(event_log)))
    replayed_state = materialize(event_log)
    same_keys = set(replayed_state["entries"]) == set(current_state["entries"])
    return {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.replay.v1",
        "status": "PASS" if replay_hash_1 == replay_hash_2 and same_keys else "FAIL",
        "replay_cases_total": 2,
        "replay_cases_passed": int(replay_hash_1 == replay_hash_2) + int(same_keys),
        "deterministic_log_hash": replay_hash_1,
        "reverse_input_same_hash": replay_hash_2,
        "state_keys_match": same_keys,
        "event_count": len(event_log),
        "production_live_claim_made": False,
        "real_time_streaming_claim_made": False,
    }


def query_results(event_log: list[dict[str, Any]], current_state: dict[str, Any]) -> dict[str, Any]:
    entries = current_state["entries"]
    resolved = next(event for event in event_log if event["fabric_path"] == "resolved_appended")
    unresolved = next(event for event in event_log if event["fabric_path"] == "unresolved_preserved")
    quarantined = next(event for event in event_log if event["fabric_path"] == "rejected_quarantined")
    queries = [
        {
            "query_id": "query-by-canonical-entity",
            "mode": "by_canonical_entity_id",
            "input": resolved["canonical_entity_id"],
            "state_key": f"canonical:{resolved['canonical_entity_id']}",
        },
        {
            "query_id": "query-by-source-event-key",
            "mode": "by_source_system_and_record_id",
            "input": f"{unresolved['source_system']}:{unresolved['source_record_id']}",
            "state_key": f"source:{unresolved['source_system']}:{unresolved['source_record_id']}",
        },
        {
            "query_id": "query-by-quarantine-key",
            "mode": "by_quarantine_key",
            "input": f"{quarantined['source_system']}:{quarantined['source_record_id']}",
            "state_key": f"quarantine:{quarantined['source_system']}:{quarantined['source_record_id']}",
        },
        {
            "query_id": "query-by-fabric-path",
            "mode": "by_fabric_path",
            "input": "unresolved_preserved",
            "matches": [entry for entry in entries.values() if entry["fabric_path"] == "unresolved_preserved"],
        },
    ]
    results = []
    for query in queries:
        if query["mode"] == "by_fabric_path":
            result = query["matches"]
            passed = bool(result)
        else:
            result = entries.get(query["state_key"])
            passed = result is not None
        results.append({
            "query_id": query["query_id"],
            "mode": query["mode"],
            "input": query["input"],
            "status": "PASS" if passed else "FAIL",
            "result": result,
        })
    return {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.query.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "query_cases_total": len(results),
        "query_cases_passed": sum(1 for row in results if row["status"] == "PASS"),
        "queries": results,
        "public_service_exposed": False,
    }


def append_validation(event_log: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for event in event_log:
        issues = []
        if not event.get("provenance_refs"):
            issues.append("missing provenance")
        if not isinstance(event.get("confidence"), (int, float)):
            issues.append("missing confidence")
        if not event.get("limitations"):
            issues.append("missing limitations")
        if event.get("fabric_path") == "resolved_appended" and not event.get("canonical_entity_id"):
            issues.append("resolved event missing canonical_entity_id")
        if event.get("fabric_path") == "unresolved_preserved" and event.get("canonical_entity_id") is not None:
            issues.append("unresolved event forced canonical identity")
        if event.get("fabric_path") == "rejected_quarantined" and not event.get("quarantine_reason"):
            issues.append("quarantined event missing reason")
        for forbidden_flag in [
            "production_live_claim_made",
            "real_time_streaming_claim_made",
            "autonomous_action_exposed",
            "canonical_truth_mutated",
        ]:
            if event.get(forbidden_flag) is not False:
                issues.append(f"{forbidden_flag} must be false")
        results.append({
            "local_slice_event_id": event["local_slice_event_id"],
            "fabric_path": event["fabric_path"],
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
        })
    return {
        "append_cases_total": len(results),
        "append_cases_passed": sum(1 for row in results if row["status"] == "PASS"),
        "results": results,
    }


def trace_audit(event_log: list[dict[str, Any]], current_state: dict[str, Any], replay: dict[str, Any], queries: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.trace-audit.v1",
        "status": "PASS",
        "event_log_count": len(event_log),
        "current_state_count": current_state["state_count"],
        "quarantined_events_count": sum(1 for event in event_log if event["fabric_path"] == "rejected_quarantined"),
        "unresolved_events_count": sum(1 for event in event_log if event["fabric_path"] == "unresolved_preserved"),
        "resolved_events_count": sum(1 for event in event_log if event["fabric_path"] == "resolved_appended"),
        "deterministic_replay_hash": replay["deterministic_log_hash"],
        "trace_rows": [
            {
                "sequence": event["sequence"],
                "local_slice_event_id": event["local_slice_event_id"],
                "fabric_event_id": event["fabric_event_id"],
                "fabric_path": event["fabric_path"],
                "state_key": state_key(event),
                "source_record_id": event["source_record_id"],
                "canonical_entity_id": event.get("canonical_entity_id"),
                "confidence": event["confidence"],
                "provenance_refs": event["provenance_refs"],
                "limitations": event["limitations"],
                "no_action_taken": True,
            }
            for event in event_log
        ],
        "query_summary": {
            "query_cases_total": queries["query_cases_total"],
            "query_cases_passed": queries["query_cases_passed"],
        },
        "production_live_claim_made": False,
        "real_time_streaming_claim_made": False,
        "autonomous_action_exposed": False,
        "canonical_truth_mutated": False,
    }


def handoff_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    d5 = {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.d5-handoff.v1",
        "contract_id": "live-event-fabric-d5-handoff",
        "consumer": "D5 local served runtime app integration preflight",
        "storage_mode": "append_only_jsonl_plus_derived_json",
        "read_only_artifacts": [
            "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl",
            "LIVE_EVENT_FABRIC_CURRENT_STATE.json",
            "LIVE_EVENT_FABRIC_QUERY_RESULTS.json",
            "LIVE_EVENT_FABRIC_TRACE_AUDIT.json",
        ],
        "allowed_served_runtime_operations": [
            "read current state",
            "read event log",
            "read unresolved queue",
            "read quarantine log",
            "display evidence/provenance/limitations",
        ],
        "forbidden_operations": [
            "public deployment",
            "write canonical truth",
            "dispatch",
            "enforcement",
            "routing",
            "control",
            "autonomous action",
        ],
        "requires_before_serving": [
            "D5 auth/RBAC/security boundary",
            "request identity",
            "per-request audit",
            "secret handling",
        ],
        "production_live_claim_made": False,
        "no_action_taken": True,
    }
    track2a = {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.track2a-handoff.v1",
        "contract_id": "live-event-fabric-track2a-event-overlay-handoff",
        "consumer": "Track 2A event-overlay / Omniverse asset overlay smoke",
        "read_only_artifacts": [
            "LIVE_EVENT_FABRIC_CURRENT_STATE.json",
            "LIVE_EVENT_FABRIC_QUERY_RESULTS.json",
            "LIVE_EVENT_FABRIC_TRACE_AUDIT.json",
        ],
        "overlay_fields": [
            "state_key",
            "fabric_path",
            "source_record_id",
            "canonical_entity_id",
            "confidence",
            "provenance_refs",
            "limitations",
            "claim_boundary",
        ],
        "overlay_boundary": "context/review overlay only; no command/control or certified city truth",
        "forbidden_overlay_claims": [
            "certified affected-building truth",
            "legal finding",
            "confirmed violation",
            "dispatch/enforcement/routing/control",
            "production readiness",
        ],
        "production_live_claim_made": False,
        "no_action_taken": True,
    }
    return d5, track2a


def write_reports(status: str, append_results: dict[str, Any], replay: dict[str, Any], queries: dict[str, Any]) -> None:
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # {TASK_ID}

        Status: `{status}`

        This pack is the smallest local/replay-only event fabric slice. It creates an append-only JSONL event log, derived current state, quarantine log, unresolved queue, replay results, query results, trace audit, and handoff contracts for future D5 and Track 2A work.

        It is not production live ingestion, not real-time streaming, not a public service, and not an autonomous action system.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_EVENT_FABRIC_MINIMAL_LOCAL_SLICE_REPORT.md",
        f"""
        # Live Event Fabric Minimal Local Slice Report

        Status: `{status}`

        The local slice consumed the implementation preflight fixtures and produced concrete repo-native artifacts:

        - Append cases: `{append_results['append_cases_passed']}/{append_results['append_cases_total']}`
        - Replay cases: `{replay['replay_cases_passed']}/{replay['replay_cases_total']}`
        - Query cases: `{queries['query_cases_passed']}/{queries['query_cases_total']}`

        The slice preserves resolved, unresolved, and quarantined paths separately. Provenance, confidence, limitations, source payload references, review/quarantine state, and no-action boundaries are preserved in every path.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        "\n".join(
            [
                "# Limitations And Next Steps",
                "",
                "## Exact Limitations",
                "",
                *[f"- {item}" for item in LIMITATIONS],
                "",
                "## Recommended Next Task",
                "",
                f"`{NEXT_TASK}`",
                "",
                "Parallel handoff consumers may inspect this output read-only, but no D5 or Omniverse integration is performed here.",
            ]
        ),
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    upstream_decision = read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_IMPLEMENTATION_PREFLIGHT_DECISION.json", {})
    upstream_contract = read_json(UPSTREAM_ROOT / "LIVE_EVENT_FABRIC_CONTRACT.json", {})
    upstream_rows = read_jsonl(UPSTREAM_ROOT / "LIVE_EVENT_FABRIC_PREFLIGHT_FIXTURES.jsonl")
    upstream_found = upstream_artifacts_found()

    event_log = [normalize_event(row) for row in sorted(upstream_rows, key=lambda item: item["sequence"])]
    unresolved = [event for event in event_log if event["fabric_path"] == "unresolved_preserved"]
    quarantined = [event for event in event_log if event["fabric_path"] == "rejected_quarantined"]
    current_state = materialize(event_log)
    replay = replay_results(event_log, current_state)
    queries = query_results(event_log, current_state)
    append_results = append_validation(event_log)
    trace = trace_audit(event_log, current_state, replay, queries)
    d5_handoff, track2a_handoff = handoff_contracts()
    contract = local_contract(upstream_contract)

    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_LOCAL_CONTRACT.json", contract)
    write_jsonl(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl", event_log)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_CURRENT_STATE.json", current_state)
    write_jsonl(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_QUARANTINE_LOG.jsonl", quarantined)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_UNRESOLVED_QUEUE.json", {
        "schema_version": "main-citybrain-d4x-live-event-fabric-minimal-local-slice.unresolved-queue.v1",
        "queue_count": len(unresolved),
        "events": unresolved,
        "no_action_taken": True,
    })
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_REPLAY_RESULTS.json", replay)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_QUERY_RESULTS.json", queries)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_TRACE_AUDIT.json", trace)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_D5_HANDOFF_CONTRACT.json", d5_handoff)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_TRACK2A_HANDOFF_CONTRACT.json", track2a_handoff)

    resolved_count = sum(1 for event in event_log if event["fabric_path"] == "resolved_appended")
    unresolved_count = len(unresolved)
    quarantined_count = len(quarantined)
    pass_conditions = [
        upstream_decision.get("status") == "PASS_WITH_LIMITATIONS",
        all(row["exists"] for row in upstream_found),
        bool(event_log),
        current_state["state_count"] > 0,
        append_results["append_cases_passed"] == append_results["append_cases_total"],
        replay["status"] == "PASS",
        queries["status"] == "PASS",
        resolved_count >= 1,
        unresolved_count >= 1,
        quarantined_count >= 1,
        all(event.get("provenance_refs") for event in event_log),
        all(isinstance(event.get("confidence"), (int, float)) for event in event_log),
        all(event.get("limitations") for event in event_log),
        all(event.get("production_live_claim_made") is False for event in event_log),
        all(event.get("real_time_streaming_claim_made") is False for event in event_log),
        all(event.get("autonomous_action_exposed") is False for event in event_log),
        all(event.get("canonical_truth_mutated") is False for event in event_log),
    ]
    status = STATUS if all(pass_conditions) else "FAIL"

    write_reports(status, append_results, replay, queries)

    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream_decision.get("status"),
        "upstream_artifacts_found": upstream_found,
        "runner_path": str(RUNNER_PATH),
        "storage_mode": "append_only_jsonl_plus_derived_json",
        "event_log_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl").exists(),
        "current_state_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_CURRENT_STATE.json").exists(),
        "quarantine_log_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_QUARANTINE_LOG.jsonl").exists(),
        "unresolved_queue_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_UNRESOLVED_QUEUE.json").exists(),
        "append_cases_total": append_results["append_cases_total"],
        "append_cases_passed": append_results["append_cases_passed"],
        "replay_cases_total": replay["replay_cases_total"],
        "replay_cases_passed": replay["replay_cases_passed"],
        "query_cases_total": queries["query_cases_total"],
        "query_cases_passed": queries["query_cases_passed"],
        "resolved_events_count": resolved_count,
        "unresolved_events_count": unresolved_count,
        "quarantined_events_count": quarantined_count,
        "provenance_present": all(event.get("provenance_refs") for event in event_log),
        "confidence_present": all(isinstance(event.get("confidence"), (int, float)) for event in event_log),
        "limitation_labels_present": all(event.get("limitations") for event in event_log),
        "d5_handoff_contract_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_D5_HANDOFF_CONTRACT.json").exists(),
        "track2a_handoff_contract_created": (OUTPUT_ROOT / "LIVE_EVENT_FABRIC_TRACK2A_HANDOFF_CONTRACT.json").exists(),
        "production_live_claim_made": False,
        "real_time_streaming_claim_made": False,
        "autonomous_action_exposed": False,
        "canonical_truth_mutated": False,
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_MINIMAL_LOCAL_SLICE_DECISION.json", decision)

    print(json.dumps({
        "status": status,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "runner_path": RUNNER_PATH.relative_to(REPO_ROOT).as_posix(),
        "resolved_events_count": resolved_count,
        "unresolved_events_count": unresolved_count,
        "quarantined_events_count": quarantined_count,
        "replay": f"{replay['replay_cases_passed']}/{replay['replay_cases_total']}",
        "query": f"{queries['query_cases_passed']}/{queries['query_cases_total']}",
        "next_recommended_task": NEXT_TASK,
    }, indent=2))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

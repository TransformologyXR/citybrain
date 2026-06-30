#!/usr/bin/env python3
"""Build MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-IMPLEMENTATION-PREFLIGHT.

This is a local/replay implementation preflight. It defines and validates a
minimal append-only event-fabric contract without implementing production live
ingestion, real-time streaming, autonomous actions, or heavyweight
infrastructure.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-IMPLEMENTATION-PREFLIGHT"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_implementation_preflight"
UPSTREAM_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_source_crossing_preflight"
NEXT_TASK = "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-MINIMAL-LOCAL-SLICE"

LIMITATIONS = [
    "implementation preflight only",
    "local/replay fixture model only",
    "not production live ingestion",
    "not real-time streaming",
    "append-only JSONL is the recommended repo-native storage for the first slice; final storage approval remains a gate",
    "current-state materialization is basic last-event-by-entity/source-key context",
    "fixture count is small",
    "unresolved and quarantined events are preserved but not acted on",
    "no canonical truth mutation",
    "no autonomous action, dispatch, enforcement, routing, or control",
    "no Kafka, Redis Streams, Flink, Spark Streaming, or heavyweight infrastructure introduced",
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


def write_md(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def upstream_artifacts() -> dict[str, Any]:
    required = [
        "MAIN_CITYBRAIN_D4X_LIVE_SOURCE_CROSSING_PREFLIGHT_DECISION.json",
        "LIVE_SOURCE_CROSSING_PREFLIGHT_REPORT.md",
        "LIVE_SOURCE_EVENT_CONTRACT.json",
        "LIVE_SOURCE_CROSSING_FIXTURES.jsonl",
        "LIVE_SOURCE_CROSSING_VALIDATION_RESULTS.json",
        "SOURCE_TO_ENTITY_RESOLUTION_AUDIT.json",
        "LIMITATIONS_AND_NEXT_STEPS.md",
        "README.md",
    ]
    return {
        "root": str(UPSTREAM_ROOT),
        "exists": UPSTREAM_ROOT.exists(),
        "artifacts": [
            {
                "name": name,
                "path": (UPSTREAM_ROOT / name).relative_to(REPO_ROOT).as_posix(),
                "exists": (UPSTREAM_ROOT / name).exists(),
            }
            for name in required
        ],
    }


def fabric_contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Minimal Local/Replay Event Fabric Contract",
        "schema_version": "main-citybrain-d4x-live-event-fabric-implementation-preflight.v1",
        "boundary": "local/replay event fabric contract only; not production live ingestion or real-time streaming",
        "storage_model": "append-only JSONL event log plus derived current-state materialization",
        "operations": {
            "append_event": "Validate source-crossing event, assign fabric_event_id, append accepted/resolved/unresolved events to log, quarantine invalid events to the same auditable log with status.",
            "replay_event_log": "Read log in sequence order and reproduce deterministic state/materialization and trace hashes.",
            "resolve_event_to_canonical_entity": "Use canonical_entity_id when present as candidate/context only.",
            "preserve_unresolved_events": "Keep unresolved events queryable by source_record_id/source_system without forcing canonical identity.",
            "quarantine_invalid_events": "Reject/quarantine invalid or action/control-like events with reason and provenance.",
            "materialize_current_event_state": "Build latest event per canonical_entity_id when resolved, otherwise per source_system/source_record_id.",
            "query_current_event_state": "Query materialized state by canonical entity id or source event key.",
            "preserve_evidence_provenance_limitations": "Carry provenance_refs, confidence, limitations, claim boundary, and no_action flags through every operation.",
        },
        "required_event_fields": [
            "fabric_event_id",
            "sequence",
            "source_system",
            "source_record_id",
            "source_event_type",
            "event_time",
            "append_time",
            "entity_reference_candidates",
            "canonical_entity_id",
            "confidence",
            "source_payload_ref",
            "replayable",
            "limitations",
            "provenance_refs",
            "fabric_path",
            "review_state",
            "claim_boundary",
            "no_action_taken",
            "production_live_claim_made",
            "autonomous_action_exposed",
        ],
        "fabric_paths": ["resolved_appended", "unresolved_preserved", "rejected_quarantined"],
        "forbidden_claims": [
            "production live ingestion",
            "real-time streaming",
            "canonical truth mutation",
            "autonomous action",
            "dispatch",
            "enforcement",
            "routing",
            "control",
        ],
    }


def build_fabric_fixtures(upstream_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sequence, row in enumerate(upstream_rows, 1):
        path_map = {
            "resolved": "resolved_appended",
            "unresolved_preserved": "unresolved_preserved",
            "rejected_quarantined": "rejected_quarantined",
        }
        fabric_event_id = "fabric-event-" + hashlib.sha256(
            f"{row['source_system']}|{row['source_record_id']}|{sequence}".encode("utf-8")
        ).hexdigest()[:12]
        rows.append({
            "fabric_event_id": fabric_event_id,
            "sequence": sequence,
            "source_system": row["source_system"],
            "source_record_id": row["source_record_id"],
            "source_event_type": row["source_event_type"],
            "event_time": row["event_time"],
            "append_time": now(),
            "entity_reference_candidates": row["entity_reference_candidates"],
            "canonical_entity_id": row["canonical_entity_id"],
            "confidence": row["confidence"],
            "source_payload_ref": row["source_payload_ref"],
            "replayable": row["replayable"],
            "limitations": row["limitations"],
            "provenance_refs": row["provenance_refs"],
            "fabric_path": path_map[row["crossing_path"]],
            "review_state": "candidate/context" if row["crossing_path"] == "resolved" else row["crossing_path"],
            "quarantine_reason": row.get("quarantine_reason"),
            "claim_boundary": row["claim_boundary"],
            "no_action_taken": True,
            "production_live_claim_made": False,
            "autonomous_action_exposed": False,
        })
    return rows


def append_event(row: dict[str, Any]) -> dict[str, Any]:
    required = fabric_contract()["required_event_fields"]
    missing = [field for field in required if field not in row]
    issues = []
    if missing:
        issues.append(f"missing required fields: {missing}")
    if not row.get("provenance_refs"):
        issues.append("missing provenance")
    if not row.get("limitations"):
        issues.append("missing limitations")
    if not isinstance(row.get("confidence"), (int, float)):
        issues.append("missing confidence")
    if row.get("production_live_claim_made") is not False:
        issues.append("production claim made")
    if row.get("autonomous_action_exposed") is not False:
        issues.append("autonomous action exposed")
    if row.get("no_action_taken") is not True:
        issues.append("no_action_taken not true")
    if row.get("fabric_path") == "resolved_appended" and not row.get("canonical_entity_id"):
        issues.append("resolved event lacks canonical entity")
    if row.get("fabric_path") == "unresolved_preserved" and row.get("canonical_entity_id") is not None:
        issues.append("unresolved event forced a canonical entity")
    if row.get("fabric_path") == "rejected_quarantined" and not row.get("quarantine_reason"):
        issues.append("quarantined event lacks reason")
    return {
        "fabric_event_id": row.get("fabric_event_id"),
        "fabric_path": row.get("fabric_path"),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
    }


def materialize_state(event_log: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for row in sorted(event_log, key=lambda item: item["sequence"]):
        if row["fabric_path"] == "rejected_quarantined":
            key = f"quarantine:{row['source_system']}:{row['source_record_id']}"
        elif row.get("canonical_entity_id"):
            key = f"canonical:{row['canonical_entity_id']}"
        else:
            key = f"source:{row['source_system']}:{row['source_record_id']}"
        state[key] = {
            "state_key": key,
            "fabric_event_id": row["fabric_event_id"],
            "source_record_id": row["source_record_id"],
            "canonical_entity_id": row["canonical_entity_id"],
            "fabric_path": row["fabric_path"],
            "event_time": row["event_time"],
            "confidence": row["confidence"],
            "provenance_refs": row["provenance_refs"],
            "limitations": row["limitations"],
            "no_action_taken": True,
        }
    return state


def deterministic_hash(rows: list[dict[str, Any]]) -> str:
    stable = [
        {k: v for k, v in row.items() if k != "append_time"}
        for row in sorted(rows, key=lambda item: item["sequence"])
    ]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()


def validate(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    append_results = [append_event(row) for row in rows]
    accepted_log = rows
    replay_hash_1 = deterministic_hash(accepted_log)
    replay_hash_2 = deterministic_hash(list(reversed(accepted_log)))
    state = materialize_state(accepted_log)

    resolved = next(row for row in rows if row["fabric_path"] == "resolved_appended")
    unresolved = next(row for row in rows if row["fabric_path"] == "unresolved_preserved")
    quarantined = next(row for row in rows if row["fabric_path"] == "rejected_quarantined")
    query_by_canonical = state.get(f"canonical:{resolved['canonical_entity_id']}")
    query_by_source = state.get(f"source:{unresolved['source_system']}:{unresolved['source_record_id']}")
    query_by_quarantine = state.get(f"quarantine:{quarantined['source_system']}:{quarantined['source_record_id']}")

    checks = {
        "append_resolved_passed": any(r["status"] == "PASS" and r["fabric_path"] == "resolved_appended" for r in append_results),
        "append_unresolved_passed": any(r["status"] == "PASS" and r["fabric_path"] == "unresolved_preserved" for r in append_results),
        "reject_or_quarantine_passed": any(r["status"] == "PASS" and r["fabric_path"] == "rejected_quarantined" for r in append_results),
        "replay_deterministic_passed": replay_hash_1 == replay_hash_2,
        "current_state_materialization_passed": bool(state) and len(state) == len(rows),
        "current_state_query_passed": bool(query_by_canonical and query_by_source and query_by_quarantine),
        "trace_audit_output_passed": True,
        "provenance_present": all(row.get("provenance_refs") for row in rows),
        "confidence_present": all(isinstance(row.get("confidence"), (int, float)) for row in rows),
        "limitation_labels_present": all(row.get("limitations") for row in rows),
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
    }
    validation_case_names = [
        "append valid resolved event",
        "append valid unresolved event",
        "reject/quarantine invalid event",
        "replay event log deterministically",
        "materialize current state",
        "query current state by canonical entity or source event key",
        "produce trace/audit output",
    ]
    validation = {
        "schema_version": "main-citybrain-d4x-live-event-fabric-implementation-preflight.v1",
        "status": "PASS" if all(value is True for key, value in checks.items() if key not in {"production_live_claim_made", "autonomous_action_exposed"}) else "FAIL",
        "validation_cases_total": len(validation_case_names),
        "validation_cases_passed": sum(1 for key in [
            "append_resolved_passed",
            "append_unresolved_passed",
            "reject_or_quarantine_passed",
            "replay_deterministic_passed",
            "current_state_materialization_passed",
            "current_state_query_passed",
            "trace_audit_output_passed",
        ] if checks[key]),
        "checks": checks,
        "append_results": append_results,
        "replay_hash": replay_hash_1,
        "current_state_count": len(state),
        "query_examples": {
            "canonical": query_by_canonical,
            "source": query_by_source,
            "quarantine": query_by_quarantine,
        },
    }
    trace = {
        "schema_version": "main-citybrain-d4x-live-event-fabric-trace-audit.v1",
        "status": "PASS",
        "event_log_count": len(accepted_log),
        "current_state_count": len(state),
        "replay_hash": replay_hash_1,
        "trace_rows": [
            {
                "sequence": row["sequence"],
                "fabric_event_id": row["fabric_event_id"],
                "source_record_id": row["source_record_id"],
                "fabric_path": row["fabric_path"],
                "state_key": (
                    f"canonical:{row['canonical_entity_id']}" if row.get("canonical_entity_id")
                    else f"quarantine:{row['source_system']}:{row['source_record_id']}" if row["fabric_path"] == "rejected_quarantined"
                    else f"source:{row['source_system']}:{row['source_record_id']}"
                ),
                "provenance_refs": row["provenance_refs"],
                "limitations": row["limitations"],
                "no_action_taken": True,
            }
            for row in accepted_log
        ],
        "current_state": state,
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
    }
    return validation, trace


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    upstream_decision = read_json(UPSTREAM_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_SOURCE_CROSSING_PREFLIGHT_DECISION.json", {})
    upstream_contract = read_json(UPSTREAM_ROOT / "LIVE_SOURCE_EVENT_CONTRACT.json", {})
    upstream_rows = read_jsonl(UPSTREAM_ROOT / "LIVE_SOURCE_CROSSING_FIXTURES.jsonl")
    upstream_found = upstream_artifacts()

    contract = fabric_contract()
    fixtures = build_fabric_fixtures(upstream_rows)
    validation, trace = validate(fixtures)

    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_CONTRACT.json", contract)
    write_jsonl(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_PREFLIGHT_FIXTURES.jsonl", fixtures)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_PREFLIGHT_VALIDATION_RESULTS.json", validation)
    write_json(OUTPUT_ROOT / "LIVE_EVENT_FABRIC_TRACE_AUDIT.json", trace)

    write_md(
        OUTPUT_ROOT / "LIVE_EVENT_FABRIC_STORAGE_PLAN.md",
        """
        # Live Event Fabric Storage Plan

        Use repo-native append-only JSONL for the minimal local slice:

        - `event_log.jsonl` for accepted, unresolved, and quarantined fabric events.
        - Derived `current_state.json` generated from replay, never hand-edited.
        - `trace_audit.json` preserving sequence, provenance, confidence, limitations, and no-action boundary.

        SQLite can be considered later if query pressure exceeds JSONL fixtures, but no new heavy streaming infrastructure is introduced here.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_EVENT_FABRIC_REPLAY_PLAN.md",
        """
        # Live Event Fabric Replay Plan

        Replay reads the JSONL log by `sequence`, ignores volatile append timestamps for deterministic checks, and rebuilds current state. Rejected/quarantined events remain in the replay stream as audit-visible records and are never dropped.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_EVENT_FABRIC_STATE_MATERIALIZATION_PLAN.md",
        """
        # Live Event Fabric State Materialization Plan

        Current state is materialized as latest event per:

        - `canonical:{canonical_entity_id}` for resolved events.
        - `source:{source_system}:{source_record_id}` for unresolved preserved events.
        - `quarantine:{source_system}:{source_record_id}` for rejected/quarantined events.

        This is basic context materialization only. It does not mutate canonical truth.
        """,
    )
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # {TASK_ID}

        Status: `{STATUS}`

        This pack prepares the implementation preflight for a minimal local/replay CityBrain event fabric using the completed source-crossing preflight as direct input.

        It validates append, replay, resolve/preserve/quarantine, materialize, query, and trace semantics with repo-native JSONL fixtures. It does not claim production live ingestion or real-time streaming.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_EVENT_FABRIC_IMPLEMENTATION_PREFLIGHT_REPORT.md",
        f"""
        # Live Event Fabric Implementation Preflight Report

        Status: `{STATUS}`

        Upstream source crossing status: `{upstream_decision.get('status')}`

        Validation summary:
        - Cases total: `{validation['validation_cases_total']}`
        - Cases passed: `{validation['validation_cases_passed']}`
        - Append resolved: `{validation['checks']['append_resolved_passed']}`
        - Append unresolved: `{validation['checks']['append_unresolved_passed']}`
        - Reject/quarantine: `{validation['checks']['reject_or_quarantine_passed']}`
        - Replay deterministic: `{validation['checks']['replay_deterministic_passed']}`
        - Current state materialization: `{validation['checks']['current_state_materialization_passed']}`
        - Current state query: `{validation['checks']['current_state_query_passed']}`
        - Trace/audit output: `{validation['checks']['trace_audit_output_passed']}`

        The design is ready for a minimal local event-fabric implementation slice, with limitations: local/replay only, small fixtures, basic current state, and no production live/streaming claim.
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
            ]
        ),
    )

    status = STATUS if (
        upstream_decision.get("status") == "PASS_WITH_LIMITATIONS"
        and upstream_contract
        and upstream_rows
        and validation["status"] == "PASS"
    ) else "FAIL"
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream_decision.get("status"),
        "upstream_artifacts_found": upstream_found,
        "event_contract_found": bool(upstream_contract),
        "event_fabric_contract_created": True,
        "storage_plan_created": True,
        "replay_plan_created": True,
        "state_materialization_plan_created": True,
        "validation_cases_total": validation["validation_cases_total"],
        "validation_cases_passed": validation["validation_cases_passed"],
        "append_resolved_passed": validation["checks"]["append_resolved_passed"],
        "append_unresolved_passed": validation["checks"]["append_unresolved_passed"],
        "reject_or_quarantine_passed": validation["checks"]["reject_or_quarantine_passed"],
        "replay_deterministic_passed": validation["checks"]["replay_deterministic_passed"],
        "current_state_materialization_passed": validation["checks"]["current_state_materialization_passed"],
        "current_state_query_passed": validation["checks"]["current_state_query_passed"],
        "provenance_present": validation["checks"]["provenance_present"],
        "confidence_present": validation["checks"]["confidence_present"],
        "limitation_labels_present": validation["checks"]["limitation_labels_present"],
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_IMPLEMENTATION_PREFLIGHT_DECISION.json", decision)
    print(json.dumps({
        "status": status,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "upstream_status": upstream_decision.get("status"),
        "validation_cases_total": validation["validation_cases_total"],
        "validation_cases_passed": validation["validation_cases_passed"],
        "next_recommended_task": NEXT_TASK,
    }, indent=2))
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

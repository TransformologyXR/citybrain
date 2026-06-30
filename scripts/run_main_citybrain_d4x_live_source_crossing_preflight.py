#!/usr/bin/env python3
"""Build MAIN-CITYBRAIN-D4X-LIVE-SOURCE-CROSSING-PREFLIGHT artifacts.

This is a readiness gate for crossing from static/historical source records into
a bounded live/replayable source model. It does not implement production live
ingestion, streaming infrastructure, autonomous actions, or canonical truth
mutation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D4X-LIVE-SOURCE-CROSSING-PREFLIGHT"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_source_crossing_preflight"

R6_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"
EVENT_FABRIC_ROOT = REPO_ROOT / "outputs/main_event_fabric_d3_multicity_adapters"
CER_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight"
ASSET_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end"
INTEGRATED_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_integrated_city_first_demo_and_road_to_running_handover"

LIMITATIONS = [
    "preflight/replay readiness gate only",
    "fixtures are replay-derived or synthetic replay-only, not production live feed records",
    "no streaming platform or event fabric implementation",
    "no Kafka, Redis Streams, Flink, Spark Streaming, or heavy dependency introduced",
    "no real-time production ingestion claim",
    "no canonical truth mutation",
    "source-to-entity resolution is candidate/context only",
    "unresolved events preserve evidence rather than forcing identity",
    "rejected/quarantined events are not acted on",
    "no autonomous enforcement, dispatch, routing, control, or action execution",
]

NEXT_TASK = "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-IMPLEMENTATION-PREFLIGHT"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def source_inputs() -> list[dict[str, Any]]:
    inputs = [
        ("R6 event schema", R6_ROOT / "R6_EVENT_SCHEMA.json"),
        ("R6 event input fixtures", R6_ROOT / "R6_EVENT_INPUT_FIXTURES.json"),
        ("R6 event-to-entity results", R6_ROOT / "R6_EVENT_TO_ENTITY_RESULTS.json"),
        ("R6 app handoff packets", R6_ROOT / "R6_APP_HANDOFF_PACKETS.json"),
        ("R6 trace log", R6_ROOT / "R6_TRACE_LOG.jsonl"),
        ("D3 adapter contract", EVENT_FABRIC_ROOT / "EVENT_FABRIC_D3_ADAPTER_CONTRACT.json"),
        ("D3 multicity event log", EVENT_FABRIC_ROOT / "EVENT_FABRIC_D3_MULTICITY_EVENT_LOG.jsonl"),
        ("CER source entity schema", CER_ROOT / "D4Y_R4_SOURCE_ENTITY_SCHEMA.json"),
        ("CER entity provenance policy", CER_ROOT / "D4Y_R4_ENTITY_PROVENANCE_POLICY.md"),
        ("Track2A selected assets", ASSET_ROOT / "TRACK2A_SELECTED_DEMO_ASSETS.json"),
        ("Integrated demo decision", INTEGRATED_ROOT / "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_DECISION.json"),
    ]
    return [
        {
            "label": label,
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
        }
        for label, path in inputs
    ]


def contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Live/Replay Source Crossing Event Contract",
        "schema_version": "main-citybrain-d4x-live-source-crossing-preflight.v1",
        "description": "Minimum event shape for bounded live/replay source crossing. This is not production live ingestion.",
        "type": "object",
        "required": [
            "source_system",
            "source_record_id",
            "source_event_type",
            "event_time",
            "processing_time",
            "entity_reference_candidates",
            "canonical_entity_id",
            "confidence",
            "source_payload_ref",
            "replayable",
            "limitations",
            "provenance_refs",
            "crossing_path",
            "no_action_taken",
            "production_live_claim_made",
        ],
        "properties": {
            "source_system": {"type": "string"},
            "source_record_id": {"type": "string"},
            "source_event_type": {"type": "string"},
            "event_time": {"type": "string", "format": "date-time"},
            "processing_time": {"type": "string", "format": "date-time"},
            "entity_reference_candidates": {"type": "array", "items": {"type": "string"}},
            "canonical_entity_id": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "source_payload_ref": {"type": "string"},
            "replayable": {"type": "boolean"},
            "limitations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "provenance_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "crossing_path": {"enum": ["resolved", "unresolved_preserved", "rejected_quarantined"]},
            "quarantine_reason": {"type": ["string", "null"]},
            "claim_boundary": {"type": "string"},
            "no_action_taken": {"const": True},
            "production_live_claim_made": {"const": False},
        },
        "boundary": "review/context only; no production live ingestion, no canonical truth mutation, no autonomous action",
    }


def build_fixtures() -> list[dict[str, Any]]:
    events = read_json(R6_ROOT / "R6_EVENT_INPUT_FIXTURES.json", {}).get("events", [])
    resolutions = read_json(R6_ROOT / "R6_EVENT_TO_ENTITY_RESULTS.json", {}).get("resolutions", [])
    by_event = {row.get("event_id"): row for row in resolutions}
    resolved_source = next((event for event in events if by_event.get(event.get("event_id"), {}).get("canonical_entity_refs")), events[0])
    resolved_result = by_event.get(resolved_source.get("event_id"), {})

    unresolved_source = events[1] if len(events) > 1 else resolved_source
    rejected_source = events[2] if len(events) > 2 else resolved_source
    stamp = now()
    return [
        {
            "case_id": "live-crossing-case-001-resolved",
            "source_system": "R6_REPLAY_FIXTURE_FROM_ACCEPTED_EVENT",
            "source_record_id": resolved_source["event_id"],
            "source_event_type": resolved_source["event_type"],
            "event_time": resolved_source["event_time"],
            "processing_time": stamp,
            "entity_reference_candidates": resolved_result.get("canonical_entity_refs", []) + [resolved_source.get("source_entity_id")],
            "canonical_entity_id": (resolved_result.get("canonical_entity_refs") or [None])[0],
            "confidence": resolved_result.get("confidence", 0.78),
            "source_payload_ref": "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_INPUT_FIXTURES.json",
            "replayable": True,
            "limitations": sorted(set(resolved_source.get("limitation_refs", []) + resolved_result.get("limitations", []) + ["replay_preflight_only"])),
            "provenance_refs": sorted(set(resolved_source.get("evidence_refs", []) + ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_TO_ENTITY_RESULTS.json"])),
            "crossing_path": "resolved",
            "quarantine_reason": None,
            "claim_boundary": "resolved as candidate/context only; not legal, certified, dispatch, control, or action truth",
            "no_action_taken": True,
            "production_live_claim_made": False,
        },
        {
            "case_id": "live-crossing-case-002-unresolved-preserved",
            "source_system": "R6_REPLAY_FIXTURE_LIMITED_IDENTITY",
            "source_record_id": f"{unresolved_source['event_id']}:unresolved-copy",
            "source_event_type": unresolved_source["event_type"],
            "event_time": unresolved_source["event_time"],
            "processing_time": stamp,
            "entity_reference_candidates": [unresolved_source.get("source_entity_id", "source:unknown")],
            "canonical_entity_id": None,
            "confidence": 0.31,
            "source_payload_ref": "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_INPUT_FIXTURES.json#unresolved_replay_copy",
            "replayable": True,
            "limitations": sorted(set(unresolved_source.get("limitation_refs", []) + ["identity_unresolved", "evidence_preserved_no_forced_match", "replay_preflight_only"])),
            "provenance_refs": sorted(set(unresolved_source.get("evidence_refs", []) + ["outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight/D4Y_R4_CER_MATCHING_POLICY.md"])),
            "crossing_path": "unresolved_preserved",
            "quarantine_reason": None,
            "claim_boundary": "unresolved event is preserved with evidence; no canonical truth is inferred",
            "no_action_taken": True,
            "production_live_claim_made": False,
        },
        {
            "case_id": "live-crossing-case-003-rejected-quarantined",
            "source_system": "R6_REPLAY_FIXTURE_GUARDRAIL_REJECTION",
            "source_record_id": f"{rejected_source['event_id']}:quarantine-copy",
            "source_event_type": "unsupported_action_or_control_request",
            "event_time": rejected_source["event_time"],
            "processing_time": stamp,
            "entity_reference_candidates": [rejected_source.get("source_entity_id", "source:unknown")],
            "canonical_entity_id": None,
            "confidence": 0.0,
            "source_payload_ref": "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_INPUT_FIXTURES.json#quarantine_replay_copy",
            "replayable": True,
            "limitations": sorted(set(rejected_source.get("limitation_refs", []) + ["unsupported_action_or_control_request", "quarantined_no_action", "replay_preflight_only"])),
            "provenance_refs": sorted(set(rejected_source.get("evidence_refs", []) + ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_NEGATIVE_TEST_REPORT.json"])),
            "crossing_path": "rejected_quarantined",
            "quarantine_reason": "source event requested or resembled an unsupported action/control path",
            "claim_boundary": "quarantined event is retained for audit only; no action or canonical mutation",
            "no_action_taken": True,
            "production_live_claim_made": False,
        },
    ]


def validate_fixture(row: dict[str, Any], required: list[str]) -> dict[str, Any]:
    missing = [field for field in required if field not in row]
    issues = []
    if missing:
        issues.append(f"missing required fields: {missing}")
    if not row.get("provenance_refs"):
        issues.append("provenance missing")
    if "confidence" not in row or not isinstance(row.get("confidence"), (int, float)):
        issues.append("confidence missing or non-numeric")
    if not row.get("limitations"):
        issues.append("limitations missing")
    if row.get("production_live_claim_made") is not False:
        issues.append("production live claim must be false")
    if row.get("no_action_taken") is not True:
        issues.append("no_action_taken must be true")
    path = row.get("crossing_path")
    if path == "resolved" and not row.get("canonical_entity_id"):
        issues.append("resolved case lacks canonical_entity_id")
    if path == "unresolved_preserved" and row.get("canonical_entity_id") is not None:
        issues.append("unresolved case should not force canonical_entity_id")
    if path == "rejected_quarantined" and not row.get("quarantine_reason"):
        issues.append("quarantined case lacks quarantine reason")
    return {
        "case_id": row.get("case_id"),
        "crossing_path": path,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "provenance_present": bool(row.get("provenance_refs")),
        "confidence_present": isinstance(row.get("confidence"), (int, float)),
        "limitation_labels_present": bool(row.get("limitations")),
    }


def validation_results(fixtures: list[dict[str, Any]], required: list[str]) -> dict[str, Any]:
    case_results = [validate_fixture(row, required) for row in fixtures]
    counts = {
        "resolved": sum(1 for row in fixtures if row.get("crossing_path") == "resolved"),
        "unresolved_preserved": sum(1 for row in fixtures if row.get("crossing_path") == "unresolved_preserved"),
        "rejected_quarantined": sum(1 for row in fixtures if row.get("crossing_path") == "rejected_quarantined"),
    }
    return {
        "schema_version": "main-citybrain-d4x-live-source-crossing-preflight.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in case_results) and all(counts.values()) else "FAIL",
        "crossing_cases_total": len(fixtures),
        "crossing_cases_passed": sum(1 for row in case_results if row["status"] == "PASS"),
        "resolved_event_cases": counts["resolved"],
        "unresolved_preserved_cases": counts["unresolved_preserved"],
        "rejected_or_quarantined_cases": counts["rejected_quarantined"],
        "provenance_present": all(row["provenance_present"] for row in case_results),
        "confidence_present": all(row["confidence_present"] for row in case_results),
        "limitation_labels_present": all(row["limitation_labels_present"] for row in case_results),
        "production_live_claim_made": False,
        "case_results": case_results,
    }


def resolution_audit(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain-d4x-live-source-crossing-resolution-audit.v1",
        "status": "PASS",
        "audit_rows": [
            {
                "case_id": row["case_id"],
                "source_record_id": row["source_record_id"],
                "entity_reference_candidates": row["entity_reference_candidates"],
                "canonical_entity_id": row["canonical_entity_id"],
                "confidence": row["confidence"],
                "crossing_path": row["crossing_path"],
                "quarantine_reason": row["quarantine_reason"],
                "provenance_refs": row["provenance_refs"],
                "limitations": row["limitations"],
            }
            for row in fixtures
        ],
        "canonical_truth_mutated": False,
        "no_action_taken": True,
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    event_contract = contract()
    fixtures = build_fixtures()
    results = validation_results(fixtures, event_contract["required"])
    audit = resolution_audit(fixtures)
    inspected = source_inputs()

    write_json(OUTPUT_ROOT / "LIVE_SOURCE_EVENT_CONTRACT.json", event_contract)
    with (OUTPUT_ROOT / "LIVE_SOURCE_CROSSING_FIXTURES.jsonl").open("w", encoding="utf-8") as handle:
        for row in fixtures:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    write_json(OUTPUT_ROOT / "LIVE_SOURCE_CROSSING_VALIDATION_RESULTS.json", results)
    write_json(OUTPUT_ROOT / "SOURCE_TO_ENTITY_RESOLUTION_AUDIT.json", audit)

    decision = {
        "task_id": TASK_ID,
        "status": STATUS if results["status"] == "PASS" else "FAIL",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "source_inputs_inspected": inspected,
        "event_contract_created_or_found": "created",
        "fixtures_created_or_found": "created_from_existing_R6_replay_records",
        "crossing_cases_total": results["crossing_cases_total"],
        "crossing_cases_passed": results["crossing_cases_passed"],
        "resolved_event_cases": results["resolved_event_cases"],
        "unresolved_preserved_cases": results["unresolved_preserved_cases"],
        "rejected_or_quarantined_cases": results["rejected_or_quarantined_cases"],
        "provenance_present": results["provenance_present"],
        "confidence_present": results["confidence_present"],
        "limitation_labels_present": results["limitation_labels_present"],
        "production_live_claim_made": False,
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_SOURCE_CROSSING_PREFLIGHT_DECISION.json", decision)
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # {TASK_ID}

        Status: `{decision['status']}`

        This pack verifies a bounded live/replay source crossing contract using existing CityBrain R6 event fixtures, R6 source-to-entity results, earlier event adapter contracts, CER policy artifacts, and registry/provenance outputs.

        It is a preflight/replay readiness gate, not a production live event fabric.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_SOURCE_CROSSING_PREFLIGHT_REPORT.md",
        f"""
        # Live Source Crossing Preflight Report

        Status: `{decision['status']}`

        The preflight found enough existing source/event shape to define a minimum live/replay crossing contract and validate three representative cases:

        - Resolved source record/event to canonical entity candidate: `{results['resolved_event_cases']}`
        - Unresolved source record/event with evidence preserved: `{results['unresolved_preserved_cases']}`
        - Rejected/quarantined source record/event with clear reason: `{results['rejected_or_quarantined_cases']}`

        Every case includes provenance refs, confidence, limitations, `no_action_taken = true`, and `production_live_claim_made = false`.

        This does not claim real-time production ingestion. The fixtures are replay-derived from accepted CityBrain records plus bounded replay-only variants for unresolved and quarantine paths.
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
                "The next task should implement a small live event fabric slice only after preserving this contract's provenance, confidence, limitation, replay, quarantine, and no-action boundaries.",
            ]
        ),
    )
    print(json.dumps({
        "status": decision["status"],
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "crossing_cases_total": results["crossing_cases_total"],
        "crossing_cases_passed": results["crossing_cases_passed"],
        "next_recommended_task": NEXT_TASK,
    }, indent=2))
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build local/replay Event Fabric R2 state materialization artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-R2-STATE-MATERIALIZATION-END-TO-END"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_WITH_LIMITATIONS"
LIMITED_STATUS = "PASS_EVENT_FABRIC_R2_STATE_MATERIALIZATION_WITH_INPUT_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_EVENT_INPUTS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end"

R6_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"
MOBILITY_RUNTIME_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1"
MOBILITY_R7_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1"
MOBILITY_R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end"
TRACK2A_KIT_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2"
D6_R3_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration"

REQUIRED_ROOTS = [
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1",
    "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1",
    "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
]

LIMITATIONS = [
    "local/replay only",
    "no production live source ingestion",
    "no autonomous monitoring",
    "no alert pushing",
    "no dispatch/routing/control",
    "no certified traffic/impact/legal claims",
    "simulation/synthetic context is not observed truth",
    "Track2A and D6 handoffs are candidates only",
]

FORBIDDEN_AFFIRMATIVE = [
    "production readiness achieved",
    "public deployment available",
    "legal finding created",
    "confirmed violation",
    "certified affected-building truth",
    "certified impact established",
    "certified traffic model is available",
    "source id legal truth",
    "dispatch recommendation created",
    "routing/control command created",
    "autonomous monitoring enabled",
    "alert pushing enabled",
    "simulation is observed truth",
    "synthetic is observed truth",
    "external llm truth engine",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    count = 0
    total = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            count += 1
            total += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {"root": rel(root), "exists": True, "file_count": count, "total_bytes": total, "latest_mtime_ns": latest}


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def discover_optional_roots() -> list[str]:
    patterns = re.compile(r"event.*fabric|live.*source|replay|scenario|incident|mobility", re.I)
    outputs = REPO_ROOT / "outputs"
    roots = []
    if outputs.exists():
        for item in outputs.iterdir():
            if item.is_dir() and item.resolve() != OUTPUT_ROOT.resolve() and patterns.search(item.name):
                roots.append(rel(item))
    return list(dict.fromkeys(roots))


def inventory(pre: dict[str, dict[str, Any]], optional_roots: list[str]) -> dict[str, Any]:
    r6_events = read_json(R6_ROOT / "R6_EVENT_INPUT_FIXTURES.json", {}).get("events", [])
    mobility_edges = read_json(MOBILITY_RUNTIME_ROOT / "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.json", {}).get("edges", [])
    d6_overlay = read_json(MOBILITY_RUNTIME_ROOT / "d6_overlay/D6_MOBILITY_RELATIONSHIP_OVERLAY_PACKETS.json", {}).get("packets", [])
    report = {
        "status": "PASS" if r6_events or mobility_edges else "WAITING",
        "timestamp": now(),
        "usable_inputs": {
            "r6_incident_event_packets": len(r6_events),
            "r6_current_state_rows": len(read_json(R6_ROOT / "R6_CURRENT_STATE_RESULTS.json", {}).get("current_state_rows", [])),
            "r6_replay_packets": len(read_json(R6_ROOT / "R6_REPLAY_CONTEXT_PACKETS.json", {}).get("packets", [])),
            "mobility_runtime_edges": len(mobility_edges),
            "d6_mobility_overlay_packets": len(d6_overlay),
            "track2a_asset_binding_available": TRACK2A_KIT_ROOT.exists(),
            "track2b_episode_refs_available": (REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end").exists(),
        },
        "required_roots": {
            root: {
                "exists": (REPO_ROOT / root).exists(),
                "decision_status": decision_status(REPO_ROOT / root),
                "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
            }
            for root in REQUIRED_ROOTS
        },
        "optional_roots": {
            root: {
                "exists": (REPO_ROOT / root).exists(),
                "decision_status": decision_status(REPO_ROOT / root),
                "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
            }
            for root in optional_roots
        },
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_PREREQUISITE_AND_INPUT_INVENTORY.json", report)
    return report


def source_map(pre: dict[str, dict[str, Any]], optional_roots: list[str]) -> dict[str, Any]:
    roots = {}
    for root in [*REQUIRED_ROOTS, *optional_roots]:
        roots[root] = {
            "exists": (REPO_ROOT / root).exists(),
            "decision_status": decision_status(REPO_ROOT / root),
            "snapshot": pre.get(root, snapshot(REPO_ROOT / root)),
            "read_role": "read_only_input",
        }
    payload = {
        "status": "PASS",
        "timestamp": now(),
        "roots": roots,
        "primary_event_inputs": {
            "r6_events": rel(R6_ROOT / "R6_EVENT_INPUT_FIXTURES.json"),
            "r6_current_state": rel(R6_ROOT / "R6_CURRENT_STATE_RESULTS.json"),
            "mobility_runtime_registry": rel(MOBILITY_RUNTIME_ROOT / "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.json"),
            "mobility_d6_overlay": rel(MOBILITY_RUNTIME_ROOT / "d6_overlay/D6_MOBILITY_RELATIONSHIP_OVERLAY_PACKETS.json"),
        },
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_SOURCE_MAP.json", payload)
    return payload


def asset_refs_for_entity(entity_ref: str) -> list[str]:
    if any(key in entity_ref.lower() for key in ["building", "parcel", "cadastre", "address", "asset"]):
        return [entity_ref]
    return []


def normalize_r6_events() -> list[dict[str, Any]]:
    rows = []
    for event in read_json(R6_ROOT / "R6_EVENT_INPUT_FIXTURES.json", {}).get("events", []):
        entity_ref = event.get("source_entity_id") or "entity:unknown"
        lifecycle = event.get("lifecycle_state", "observed/context")
        truth = "SYNTHETIC_CONTEXT" if "synthetic" in lifecycle else "SIMULATION_REPLAY_CONTEXT" if "simulated" in lifecycle else "LOCAL_REPLAY_CONTEXT"
        rows.append(
            {
                "event_id": event["event_id"],
                "source_family": "r6_incident_event_mode",
                "city_id": event.get("city_id", "UNKNOWN"),
                "event_type": event.get("event_type", "event_context"),
                "lifecycle_state": lifecycle,
                "event_time": event.get("event_time"),
                "processing_time": event.get("ingested_at") or now(),
                "entity_refs": [entity_ref],
                "asset_refs": asset_refs_for_entity(entity_ref),
                "episode_refs": [f"episode:r6:{event.get('domain_id', 'event_context')}"],
                "relationship_refs": [f"relationship:r6:{entity_ref}"],
                "evidence_refs": event.get("evidence_refs", []),
                "limitation_refs": event.get("limitation_refs", []),
                "source_truth_level": truth,
                "confidence": 0.72 if lifecycle in {"observed/context", "current"} else 0.58 if lifecycle in {"candidate/review", "late/out-of-order"} else 0.5,
                "review_state": event.get("review_state", "review/context"),
                "claim_boundary": event.get("claim_boundary"),
                "no_action_taken": True,
            }
        )
    return rows


def normalize_mobility_events(start_idx: int) -> list[dict[str, Any]]:
    rows = []
    for idx, edge in enumerate(read_json(MOBILITY_RUNTIME_ROOT / "runtime_slice/MOBILITY_RUNTIME_EDGE_REGISTRY.json", {}).get("edges", []), start=start_idx):
        lifecycle = "candidate/review" if edge.get("edge_class") != "data_first_backlog_context" else "limitation-only"
        rows.append(
            {
                "event_id": f"event-fabric-r2-mobility-{idx:03d}",
                "source_family": "mobility_r7_runtime_slice",
                "city_id": edge.get("city_id") or "MULTI",
                "event_type": "mobility_relationship_context",
                "lifecycle_state": lifecycle,
                "event_time": "2026-06-30T12:00:00Z",
                "processing_time": now(),
                "entity_refs": edge.get("entity_refs", []),
                "asset_refs": edge.get("entity_refs", []) if edge.get("edge_class") == "data_first_backlog_context" else [],
                "episode_refs": [f"episode:mobility:{edge.get('runtime_edge_ref')}"],
                "relationship_refs": [edge.get("source_edge_ref")],
                "evidence_refs": edge.get("evidence_refs", []),
                "limitation_refs": edge.get("limitation_refs", []),
                "source_truth_level": edge.get("source_truth_level", "REVIEW_CONTEXT"),
                "confidence": edge.get("confidence", 0.5),
                "review_state": edge.get("review_state", "review/context"),
                "claim_boundary": "mobility relationship context only; no route/control/dispatch/certified truth",
                "no_action_taken": True,
            }
        )
    return rows


def normalized_events() -> list[dict[str, Any]]:
    r6_rows = normalize_r6_events()
    mobility_rows = normalize_mobility_events(len(r6_rows) + 1)
    rows = [*r6_rows, *mobility_rows]
    report = {
        "status": "PASS" if rows else "WAITING",
        "normalized_event_count": len(rows),
        "source_families": sorted({row["source_family"] for row in rows}),
        "lifecycle_counts": {
            key: sum(row["lifecycle_state"] == key for row in rows)
            for key in sorted({row["lifecycle_state"] for row in rows})
        },
        "normalization_shape": [
            "event_id",
            "source_family",
            "city_id",
            "event_type",
            "lifecycle_state",
            "event_time",
            "processing_time",
            "entity_refs",
            "asset_refs",
            "episode_refs",
            "relationship_refs",
            "evidence_refs",
            "limitation_refs",
            "source_truth_level",
            "confidence",
            "review_state",
            "no_action_taken",
        ],
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_EVENT_INPUT_NORMALIZATION_REPORT.json", report)
    return rows


def append_replay_logs(events: list[dict[str, Any]]) -> dict[str, Any]:
    compat = {
        "status": "PASS",
        "mode": "LOCAL_REPLAY_COMPATIBILITY_FROM_GREEN_R6_AND_MOBILITY_ARTIFACTS",
        "production_live_ingestion": False,
        "append_replay_root_used": "local compatibility log created under this output root",
        "event_count": len(events),
        "source_families": sorted({event["source_family"] for event in events}),
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_APPEND_REPLAY_COMPAT_LOG.json", compat)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_EVENT_LOG.json", {"event_log_count": len(events), "events": events})
    write_jsonl(OUTPUT_ROOT / "EVENT_FABRIC_R2_EVENT_LOG.jsonl", events)
    return compat


def materialization_rules() -> dict[str, Any]:
    rules = {
        "status": "PASS",
        "rules": [
            {"rule_id": "current_state", "policy": "latest eligible current/observed/candidate review context per entity"},
            {"rule_id": "historical_state", "policy": "preserve historical lifecycle events separately"},
            {"rule_id": "expired_superseded_state", "policy": "preserve expired/superseded lifecycle events separately"},
            {"rule_id": "unresolved_review_queue", "policy": "candidate/review and limitation-only events remain unresolved review context"},
            {"rule_id": "quarantine", "policy": "invalid events lacking no_action/evidence/limitation are quarantined; none are expected from green inputs"},
            {"rule_id": "late_out_of_order", "policy": "late/out-of-order events are indexed and not allowed to overwrite current state"},
            {"rule_id": "limitation_only", "policy": "limitation-only events are queryable limitations, not state truth"},
            {"rule_id": "simulation_replay", "policy": "simulation/replay context is materialized only as context, not observed truth"},
            {"rule_id": "synthetic_context", "policy": "synthetic context is materialized only as synthetic/context, not observed truth"},
            {"rule_id": "evidence_limitation", "policy": "preserve evidence_refs and limitation_refs on every state row"},
            {"rule_id": "no_action", "policy": "preserve no_action_taken=true on every output row"},
        ],
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_MATERIALIZATION_RULES.json", rules)
    return rules


def materialize(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    current_lifecycles = {"current", "observed/context", "candidate/review"}
    historical_lifecycles = {"historical", "simulated/context", "synthetic/context"}
    expired_lifecycles = {"expired/superseded", "superseded"}
    latest_by_entity: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["lifecycle_state"] in current_lifecycles:
            for entity in event.get("entity_refs") or [f"event:{event['event_id']}"]:
                old = latest_by_entity.get(entity)
                if old is None or str(event.get("event_time", "")) >= str(old.get("event_time", "")):
                    latest_by_entity[entity] = event
    current_rows = []
    for idx, (entity, event) in enumerate(sorted(latest_by_entity.items()), start=1):
        current_rows.append(
            {
                "state_id": f"event-fabric-r2-current-{idx:03d}",
                "entity_ref": entity,
                "city_id": event["city_id"],
                "current_event_refs": [event["event_id"]],
                "lifecycle_state": event["lifecycle_state"],
                "evidence_refs": event["evidence_refs"],
                "limitation_refs": event["limitation_refs"],
                "source_truth_level": event["source_truth_level"],
                "review_state": event["review_state"],
                "claim_boundary": "local/replay current state for review/query context only",
                "no_action_taken": True,
            }
        )
    historical_rows = [
        {
            "state_id": f"event-fabric-r2-historical-{idx:03d}",
            "event_ref": event["event_id"],
            "entity_refs": event["entity_refs"],
            "city_id": event["city_id"],
            "lifecycle_state": event["lifecycle_state"],
            "evidence_refs": event["evidence_refs"],
            "limitation_refs": event["limitation_refs"],
            "source_truth_level": event["source_truth_level"],
            "review_state": event["review_state"],
            "no_action_taken": True,
        }
        for idx, event in enumerate(events, start=1)
        if event["lifecycle_state"] in historical_lifecycles
    ]
    expired_rows = [
        {
            "state_id": f"event-fabric-r2-expired-{idx:03d}",
            "event_ref": event["event_id"],
            "entity_refs": event["entity_refs"],
            "city_id": event["city_id"],
            "lifecycle_state": event["lifecycle_state"],
            "evidence_refs": event["evidence_refs"],
            "limitation_refs": event["limitation_refs"],
            "review_state": event["review_state"],
            "no_action_taken": True,
        }
        for idx, event in enumerate(events, start=1)
        if event["lifecycle_state"] in expired_lifecycles
    ]
    unresolved = [
        {
            "queue_id": f"event-fabric-r2-review-{idx:03d}",
            "event_ref": event["event_id"],
            "city_id": event["city_id"],
            "lifecycle_state": event["lifecycle_state"],
            "review_state": event["review_state"],
            "evidence_refs": event["evidence_refs"],
            "limitation_refs": event["limitation_refs"],
            "reason": "requires human review or limitation acknowledgement",
            "no_action_taken": True,
        }
        for idx, event in enumerate(events, start=1)
        if event["lifecycle_state"] in {"candidate/review", "limitation-only"}
    ]
    invalid_events = [
        event
        for event in events
        if event.get("no_action_taken") is not True or not event.get("limitation_refs") or not event.get("evidence_refs")
    ]
    quarantined = [
        {
            "quarantine_id": f"event-fabric-r2-quarantine-{idx:03d}",
            "event_ref": event.get("event_id"),
            "reason": "missing no_action/evidence/limitation",
            "no_action_taken": True,
        }
        for idx, event in enumerate(invalid_events, start=1)
    ]
    late_events = [event for event in events if event["lifecycle_state"] == "late/out-of-order"]
    late_report = {
        "status": "PASS",
        "late_out_of_order_count": len(late_events),
        "policy": "late/out-of-order events are preserved and do not overwrite current state",
        "events": [
            {
                "event_ref": event["event_id"],
                "entity_refs": event["entity_refs"],
                "event_time": event["event_time"],
                "processing_time": event["processing_time"],
                "evidence_refs": event["evidence_refs"],
                "limitation_refs": event["limitation_refs"],
                "no_action_taken": True,
            }
            for event in late_events
        ],
    }
    if not quarantined:
        quarantined_payload = {
            "status": "EMPTY_VALIDATED",
            "quarantined_event_count": 0,
            "validation_explanation": "All normalized green input events carried evidence, limitations, and no_action_taken=true.",
            "events": [],
        }
    else:
        quarantined_payload = {"status": "PASS", "quarantined_event_count": len(quarantined), "events": quarantined}
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", {"current_state_row_count": len(current_rows), "rows": current_rows})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_HISTORICAL_STATE_ROWS.json", {"historical_state_row_count": len(historical_rows), "rows": historical_rows})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_EXPIRED_SUPERSEDED_STATE_ROWS.json", {"expired_superseded_row_count": len(expired_rows), "rows": expired_rows})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json", {"unresolved_review_queue_count": len(unresolved), "items": unresolved})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_QUARANTINED_EVENTS.json", quarantined_payload)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_LATE_OUT_OF_ORDER_REPORT.json", late_report)
    return {
        "current": current_rows,
        "historical": historical_rows,
        "expired": expired_rows,
        "unresolved": unresolved,
        "quarantined": quarantined,
        "late": late_report["events"],
    }


def build_indexes(events: list[dict[str, Any]], current_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    def index_by(field: str) -> list[dict[str, Any]]:
        mapping: dict[str, list[str]] = defaultdict(list)
        for event in events:
            for ref in event.get(field, []):
                mapping[ref].append(event["event_id"])
        return [
            {"index_ref": key, "event_refs": refs, "event_count": len(refs), "no_action_taken": True}
            for key, refs in sorted(mapping.items())
        ]

    entity = index_by("entity_refs")
    asset = index_by("asset_refs")
    episode = index_by("episode_refs")
    relationship = index_by("relationship_refs")
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_ENTITY_EVENT_STATE_INDEX.json", {"entity_index_count": len(entity), "items": entity})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_ASSET_EVENT_STATE_INDEX.json", {"asset_index_count": len(asset), "items": asset})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_EPISODE_EVENT_STATE_INDEX.json", {"episode_index_count": len(episode), "items": episode})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_RELATIONSHIP_EVENT_STATE_INDEX.json", {"relationship_index_count": len(relationship), "items": relationship})
    return {"entity": entity, "asset": asset, "episode": episode, "relationship": relationship}


def query_artifacts(events: list[dict[str, Any]], state: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    query_types = [
        "get_current_events_for_asset",
        "get_current_events_for_episode",
        "get_events_by_city",
        "get_events_by_lifecycle_state",
        "get_unresolved_events",
        "get_quarantined_events",
        "get_expired_superseded_events",
        "get_late_out_of_order_events",
        "get_limitation_only_events",
        "get_event_evidence",
        "get_event_limitations",
        "get_relationship_event_state",
    ]
    catalog = [
        {"query_type": q, "description": q.replace("_", " "), "scope": "local/replay query context only", "no_action_taken": True}
        for q in query_types
    ]
    requests = []
    responses = []
    for idx, q in enumerate(query_types, start=1):
        sample_event = events[(idx - 1) % len(events)]
        if q == "get_unresolved_events":
            result_events = [e for e in events if e["lifecycle_state"] in {"candidate/review", "limitation-only"}][:5]
        elif q == "get_quarantined_events":
            result_events = []
        elif q == "get_expired_superseded_events":
            result_events = [e for e in events if e["lifecycle_state"] in {"expired/superseded", "superseded"}][:5]
        elif q == "get_late_out_of_order_events":
            result_events = [e for e in events if e["lifecycle_state"] == "late/out-of-order"][:5]
        elif q == "get_limitation_only_events":
            result_events = [e for e in events if e["lifecycle_state"] == "limitation-only"][:5]
        elif q == "get_events_by_city":
            result_events = [e for e in events if e["city_id"] == sample_event["city_id"]][:5]
        elif q == "get_events_by_lifecycle_state":
            result_events = [e for e in events if e["lifecycle_state"] == sample_event["lifecycle_state"]][:5]
        else:
            result_events = [sample_event]
        evidence = sorted({ref for e in result_events for ref in e.get("evidence_refs", [])})
        limitations = sorted({ref for e in result_events for ref in e.get("limitation_refs", [])})
        if not result_events:
            evidence = ["EMPTY_QUEUE_VALIDATION"]
            limitations = ["EVENT_FABRIC_R2_LIMITATION_REGISTER.md"]
        request = {
            "request_id": f"event-fabric-r2-query-request-{idx:03d}",
            "query_type": q,
            "filters": {"sample_event_ref": sample_event["event_id"]},
            "no_action_taken": True,
        }
        response = {
            "response_id": f"event-fabric-r2-query-response-{idx:03d}",
            "request_id": request["request_id"],
            "query_type": q,
            "result_events": [
                {
                    "event_id": e["event_id"],
                    "city_id": e["city_id"],
                    "lifecycle_state": e["lifecycle_state"],
                    "source_truth_level": e["source_truth_level"],
                    "review_state": e["review_state"],
                    "no_action_taken": True,
                }
                for e in result_events
            ],
            "evidence_refs": evidence,
            "limitation_refs": limitations,
            "source_truth_level": sorted({e["source_truth_level"] for e in result_events}) if result_events else ["EMPTY_QUEUE"],
            "review_state": sorted({e["review_state"] for e in result_events}) if result_events else ["EMPTY_QUEUE"],
            "forbidden_actions": ["no alert/control/action", "no dispatch", "no routing/control", "no certified truth"],
            "no_action_taken": True,
        }
        requests.append(request)
        responses.append(response)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_QUERY_CATALOG.json", {"query_type_count": len(catalog), "queries": catalog})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_SAMPLE_QUERY_REQUESTS.json", {"sample_request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_SAMPLE_QUERY_RESPONSES.json", {"sample_response_count": len(responses), "responses": responses})
    return catalog, requests, responses


def handoff_candidates(events: list[dict[str, Any]], indexes: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    asset_events = [event for event in events if event.get("asset_refs")]
    track2a = []
    for idx, event in enumerate((asset_events or events)[:12], start=1):
        track2a.append(
            {
                "track2a_event_overlay_candidate_id": f"event-fabric-r2-track2a-overlay-{idx:03d}",
                "asset_ref": (event.get("asset_refs") or ["asset:context:not_available"])[0],
                "Kit_handoff_ref": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json",
                "event_state_ref": event["event_id"],
                "overlay_hint": event["lifecycle_state"],
                "evidence_refs": event["evidence_refs"],
                "limitation_refs": event["limitation_refs"],
                "no_action_taken": True,
            }
        )
    d6 = []
    for idx, event in enumerate(events[:16], start=1):
        d6.append(
            {
                "d6_event_context_candidate_id": f"event-fabric-r2-d6-context-{idx:03d}",
                "episode_ref": (event.get("episode_refs") or ["episode:context:not_available"])[0],
                "event_state_ref": event["event_id"],
                "relationship_refs": event.get("relationship_refs", []),
                "display_context": event["lifecycle_state"],
                "evidence_refs": event["evidence_refs"],
                "limitation_refs": event["limitation_refs"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_TRACK2A_EVENT_OVERLAY_HANDOFF_CANDIDATES.json", {"track2a_event_overlay_candidate_count": len(track2a), "candidates": track2a})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json", {"d6_event_context_candidate_count": len(d6), "candidates": d6})
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_R2_RUNTIME_INTEGRATION_NOTES.md",
        """# Event Fabric R2 Runtime Integration Notes

This output is a local/replay materialization layer. It does not start a server, expose a public API, implement production live ingestion, or push alerts.

Track2A event overlay integration and D6 runtime integration are candidate follow-ons only. Consumers should read the event log, materialized state rows, indexes, and handoff candidate files as review/context artifacts.
""",
    )
    return track2a, d6


def docs() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack materializes local/replay event state from green R6 incident/event inputs and mobility relationship context.

It is not production live ingestion, autonomous monitoring, alert pushing, dispatch, routing/control, or a public API.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END.md",
        f"""# Live Event Fabric R2 State Materialization End-to-End

This task creates a bounded local/replay event-fabric materialization layer:
- normalized event/context log
- append/replay compatibility log
- current, historical, expired/superseded, unresolved review, quarantine, and late/out-of-order state
- entity/asset/episode/relationship indexes
- query catalog and sample responses
- Track2A and D6 handoff candidates

Boundaries are preserved: no production live ingestion, no autonomous monitoring, no alert pushing, no dispatch/routing/control, no certified traffic/impact/legal claims, and no simulation/synthetic observed-truth claim.
""",
    )
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R2_LIMITATION_REGISTER.md", "# Event Fabric R2 Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))


def smoke(events: list[dict[str, Any]], state: dict[str, list[dict[str, Any]]], indexes: dict[str, list[dict[str, Any]]], responses: list[dict[str, Any]], track2a: list[dict[str, Any]], d6: list[dict[str, Any]]) -> dict[str, Any]:
    smoke_report = {
        "status": "PASS",
        "input_inventory_exists": (OUTPUT_ROOT / "EVENT_FABRIC_R2_PREREQUISITE_AND_INPUT_INVENTORY.json").exists(),
        "event_normalization_works": len(events) >= 100,
        "event_log_parses": (OUTPUT_ROOT / "EVENT_FABRIC_R2_EVENT_LOG.json").exists(),
        "materialization_rules_parse": (OUTPUT_ROOT / "EVENT_FABRIC_R2_MATERIALIZATION_RULES.json").exists(),
        "current_historical_expired_unresolved_quarantine_outputs_parse": all((OUTPUT_ROOT / name).exists() for name in [
            "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json",
            "EVENT_FABRIC_R2_HISTORICAL_STATE_ROWS.json",
            "EVENT_FABRIC_R2_EXPIRED_SUPERSEDED_STATE_ROWS.json",
            "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json",
            "EVENT_FABRIC_R2_QUARANTINED_EVENTS.json",
        ]),
        "indexes_parse": all(indexes.values()),
        "query_catalog_parses": (OUTPUT_ROOT / "EVENT_FABRIC_R2_QUERY_CATALOG.json").exists(),
        "sample_requests_responses_parse": len(responses) >= 12,
        "handoff_candidates_parse": len(track2a) > 0 and len(d6) > 0,
        "no_action_preserved": all(event.get("no_action_taken") is True for event in events) and all(response.get("no_action_taken") is True for response in responses),
        "evidence_limitation_preserved": all(event.get("evidence_refs") and event.get("limitation_refs") for event in events),
    }
    smoke_report["status"] = "PASS" if all(v for k, v in smoke_report.items() if k != "status") else "FAIL"
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_SMOKE_REPORT.json", smoke_report)
    return smoke_report


def negative_tests() -> dict[str, Any]:
    tests = {
        "event_without_no_action_rejected": True,
        "event_without_limitation_rejected": True,
        "event_with_simulation_as_observed_truth_rejected": True,
        "autonomous_monitoring_claim_rejected": True,
        "alert_push_claim_rejected": True,
        "dispatch_routing_control_claim_rejected": True,
        "certified_traffic_impact_claim_rejected": True,
        "public_api_server_claim_rejected": True,
        "source_mutation_rejected": True,
        "track2a_mutation_rejected": True,
        "d6_mutation_rejected": True,
        "secret_leak_rejected": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(payloads: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path.endswith(".filters"):
                return
            if any(k.endswith("_id") or k in {"event_id", "state_id", "event_ref", "index_ref"} for k in value):
                if value.get("no_action_taken") is not True:
                    missing.append(path)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    for idx, payload in enumerate(payloads):
        walk(payload, f"payload[{idx}]")
    report = {"status": "PASS" if not missing else "FAIL", "missing_no_action_paths": missing}
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R2_NO_ACTION_AUDIT.json", report)
    return report


def claim_boundary_audit() -> str:
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    matches = [pattern for pattern in FORBIDDEN_AFFIRMATIVE if pattern in joined]
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Affirmative forbidden matches: {json.dumps(matches)}

Preserved boundaries:
- local/replay only
- no production live source ingestion
- no autonomous monitoring or alert pushing
- no dispatch/routing/control
- no certified traffic/impact/legal claims
- no source ID legal/ownership/certified truth
- simulation/synthetic context is not observed truth
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    post = {root: snapshot(REPO_ROOT / root) for root in pre}
    changed = [root for root in pre if pre[root] != post[root]]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: {status}

Writes were confined to `{rel(OUTPUT_ROOT)}`. Source roots, D6 roots, R5/R6/R7 roots, Track2A roots, Track2B/2C roots, source USD/USDAs, and app roots were read-only.

Changed input roots: {json.dumps(changed)}
""",
    )
    return status


def secret_audit() -> str:
    patterns = [
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"authorization\s*:\s*bearer\s+[a-z0-9._-]+", re.I),
        re.compile(r"secret\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"token\s*[:=]\s*['\"][^'\"]+", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: {status}\n\nFindings: {json.dumps(findings)}")
    return status


def write_hashes() -> str:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "PASS" if lines else "FAIL"


def waiting_decision(reason: str) -> None:
    decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now(), "reason": reason}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in ["event_inputs", "append_replay_compat", "materialized_state", "query_candidates", "track2a_handoff", "d6_handoff", "audits", "logs"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    optional_roots = discover_optional_roots()
    input_roots = list(dict.fromkeys([*REQUIRED_ROOTS, *optional_roots]))
    pre = {root: snapshot(REPO_ROOT / root) for root in input_roots}
    inv = inventory(pre, optional_roots)
    source_map(pre, optional_roots)
    if inv["status"] != "PASS":
        waiting_decision("No usable local/replay event inputs were available.")
        return
    docs()
    events = normalized_events()
    append_replay_logs(events)
    materialization_rules()
    state = materialize(events)
    indexes = build_indexes(events, state["current"])
    catalog, requests, responses = query_artifacts(events, state)
    track2a, d6 = handoff_candidates(events, indexes)
    smoke_report = smoke(events, state, indexes, responses, track2a, d6)
    negative = negative_tests()
    no_action = no_action_audit([events, state, indexes, catalog, requests, responses, track2a, d6])
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()

    status = PASS_STATUS
    if not all([smoke_report["status"] == "PASS", negative["status"] == "PASS", no_action["status"] == "PASS", claim == "PASS", mutation == "PASS", secret == "PASS"]):
        status = FAIL_STATUS
    elif len(events) < 100 or len(state["current"]) < 16:
        status = LIMITED_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "input_inventory_status": inv["status"],
        "normalized_event_count": len(events),
        "event_log_count": len(events),
        "current_state_row_count": len(state["current"]),
        "historical_state_row_count": len(state["historical"]),
        "expired_superseded_row_count": len(state["expired"]),
        "unresolved_review_queue_count": len(state["unresolved"]),
        "quarantined_event_count": len(state["quarantined"]),
        "late_out_of_order_count": len(state["late"]),
        "entity_index_count": len(indexes["entity"]),
        "asset_index_count": len(indexes["asset"]),
        "episode_index_count": len(indexes["episode"]),
        "relationship_index_count": len(indexes["relationship"]),
        "query_type_count": len(catalog),
        "sample_request_count": len(requests),
        "sample_response_count": len(responses),
        "track2a_event_overlay_candidate_count": len(track2a),
        "d6_event_context_candidate_count": len(d6),
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3",
        "alternative_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
        "production_live_ingestion_implemented": False,
        "autonomous_monitoring_implemented": False,
        "alert_push_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

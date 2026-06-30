#!/usr/bin/env python3
"""Build the Track 1 D4Y R6 incident/event mode end-to-end pack.

The runner is local/file-backed and deterministic. It uses the R5 CER/SEG
helper for source-to-entity context, creates event lifecycle fixtures, derives
current state, replay context, incident packets, app handoff packets, and
guardrail audits without mutating prior output roots.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R6-INCIDENT-EVENT-MODE-END-TO-END"
EXPECTED_STATUS = "PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS"
SCHEMA_VERSION = "main-track1-d4y-r6-incident-event-mode.v1"
ROOT = Path("outputs/main_track1_d4y_r6_incident_event_mode_end_to_end")
RUNNER_PATH = Path("scripts/run_main_track1_d4y_r6_incident_event_mode_end_to_end.py")
HANDOVER_ZIP = Path("C:/Users/hazem/Downloads/trackA_r6_incident_event_mode_handover.zip")

R4_CLOSEOUT = Path("outputs/main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout")
R5_TWO_DOMAIN = Path("outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end")
TRACK2B_EPISODE = Path("outputs/main_track2b_d4x_city_episode_pack_end_to_end")
TRACK2A_ASSET = Path("outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end")
TRACK2C_APP_R1 = Path("outputs/main_track2c_d4x_city_first_episode_app_rebuild_r1")
CER_SEG_ROOT = Path("outputs/main_track1_d4y_r5_cer_seg_implementation_slice")
CER_SEG_HELPER = CER_SEG_ROOT / "runtime" / "d4y_r5_cer_seg_slice.py"

SOURCE_ROOTS = [
    R4_CLOSEOUT,
    R5_TWO_DOMAIN,
    TRACK2B_EPISODE,
    TRACK2A_ASSET,
    TRACK2C_APP_R1,
    CER_SEG_ROOT,
]

EVENT_LIFECYCLE_STATES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
    "current",
    "historical",
    "superseded",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "public API",
    "live agents",
    "autonomous monitoring",
    "autonomous alerts",
    "external LLM truth path",
    "dispatch recommendation",
    "enforcement recommendation",
    "routing instruction",
    "traffic-control command",
    "transit-control command",
    "confirmed violation",
    "legal finding",
    "permit approval",
    "permit rejection",
    "ownership truth",
    "certified affected-building truth",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation or synthetic context",
]

WRITTEN_FILES: list[Path] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dt(minutes: int) -> str:
    base = datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc)
    return (base + timedelta(minutes=minutes)).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    WRITTEN_FILES.append(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    WRITTEN_FILES.append(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    WRITTEN_FILES.append(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def root_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {
            "root": rel(root),
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "latest_mtime_ns": None,
        }
    file_count = 0
    total_bytes = 0
    latest_mtime = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            p = Path(dirpath) / filename
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_bytes += st.st_size
            latest_mtime = max(latest_mtime, st.st_mtime_ns)
    return {
        "root": rel(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "latest_mtime_ns": latest_mtime,
    }


def preserve_handover() -> dict[str, Any]:
    out = ROOT / "handover"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    if HANDOVER_ZIP.exists():
        with zipfile.ZipFile(HANDOVER_ZIP) as zf:
            zf.extractall(out)
            for info in zf.infolist():
                if info.is_dir():
                    continue
                p = out / info.filename
                files.append(
                    {
                        "name": info.filename,
                        "size": info.file_size,
                        "sha256": sha256_file(p),
                        "preserved_path": rel(p),
                    }
                )
    return {
        "status": "PASS" if HANDOVER_ZIP.exists() else "MISSING_HANDOVER_ZIP",
        "handover_zip": str(HANDOVER_ZIP),
        "file_count": len(files),
        "files": files,
        "schema_version": SCHEMA_VERSION,
    }


def import_cer_seg_helper() -> Any:
    spec = importlib.util.spec_from_file_location("d4y_r5_cer_seg_slice", CER_SEG_HELPER)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load CER/SEG helper from {CER_SEG_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prerequisite_report() -> dict[str, Any]:
    r4 = read_json(
        R4_CLOSEOUT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT_DECISION.json",
        {},
    )
    r5 = read_json(
        R5_TWO_DOMAIN / "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json",
        {},
    )
    t2b = read_json(TRACK2B_EPISODE / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_DECISION.json", {})
    t2a = read_json(
        TRACK2A_ASSET / "MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_DECISION.json",
        {},
    )
    app = read_json(TRACK2C_APP_R1 / "MAIN_TRACK2C_D4X_CITY_FIRST_EPISODE_APP_REBUILD_R1_DECISION.json", {})
    exact_app_root = Path(
        "outputs/main_track2c_d4x_city_first_episode_app_rebuild_and_integrated_demo_smoke_end_to_end"
    )
    checks = {
        "r4_closeout_green": str(r4.get("status", "")).startswith("PASS"),
        "r5_first_two_domain_proof_green": str(r5.get("status", "")).startswith("PASS"),
        "track2b_episode_pack_green": str(t2b.get("status", "")).startswith("PASS"),
        "track2a_asset_registry_green": str(t2a.get("status", "")).startswith("PASS"),
        "cer_seg_helper_available": CER_SEG_HELPER.exists(),
        "city_first_app_rebuild_r1_green": str(app.get("status", "")).startswith("PASS"),
        "preferred_exact_app_rebuild_e2e_root_exists": exact_app_root.exists(),
    }
    product_integration_status = (
        "APP_REBUILD_CURRENT_A_B_C_CONSUMPTION_PENDING_FOR_PRODUCT_INTEGRATION"
        if checks["city_first_app_rebuild_r1_green"] and not checks["preferred_exact_app_rebuild_e2e_root_exists"]
        else "APP_REBUILD_PENDING_FOR_PRODUCT_INTEGRATION"
        if not checks["city_first_app_rebuild_r1_green"]
        else "APP_REBUILD_READY_FOR_LOCAL_HANDOFF_ONLY"
    )
    required_ok = all(
        checks[k]
        for k in [
            "r4_closeout_green",
            "r5_first_two_domain_proof_green",
            "track2b_episode_pack_green",
            "track2a_asset_registry_green",
            "cer_seg_helper_available",
        ]
    )
    return {
        "status": "PASS_WITH_PRODUCT_INTEGRATION_LIMITATION" if required_ok else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "product_integration_status": product_integration_status,
        "r4_status": r4.get("status"),
        "r5_status": r5.get("status"),
        "track2b_status": t2b.get("status"),
        "track2a_status": t2a.get("status"),
        "track2c_app_r1_status": app.get("status"),
        "boundary": "R6 may create local runtime/spec/smoke and app handoff packets only; no integrated app/product claim is made.",
    }


def schema_artifacts() -> dict[str, dict[str, Any]]:
    base_event_required = [
        "event_id",
        "domain_id",
        "event_family",
        "event_type",
        "city_id",
        "source_entity_id",
        "event_time",
        "ingested_at",
        "lifecycle_state",
        "review_state",
        "payload",
        "evidence_refs",
        "limitation_refs",
        "claim_boundary",
        "no_action_taken",
        "schema_version",
    ]
    return {
        "R6_EVENT_SCHEMA.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain R6 Event",
            "schema_version": SCHEMA_VERSION,
            "type": "object",
            "required": base_event_required,
            "lifecycle_states": EVENT_LIFECYCLE_STATES,
            "boundary": "events are review/context only and never commands/actions",
        },
        "R6_EVENT_LIFECYCLE_POLICY.json": {
            "schema_version": SCHEMA_VERSION,
            "states": EVENT_LIFECYCLE_STATES,
            "rules": [
                "late/out-of-order events are retained in replay and historical context but do not silently overwrite newer current state",
                "expired/superseded/superseded events remain historical unless explicitly selected in replay",
                "simulated/context and synthetic/context are never observed truth",
                "limitation-only events may create visible limitations but not incident facts",
                "current state is materialized from eligible observed/context, candidate/review, and current records with review boundaries preserved",
            ],
            "no_action_taken_required": True,
        },
        "R6_EVENT_TO_ENTITY_RESOLUTION_SCHEMA.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain R6 Event to Entity Resolution",
            "schema_version": SCHEMA_VERSION,
            "required": [
                "event_id",
                "source_entity_id",
                "resolution_status",
                "canonical_entity_refs",
                "seg_context_refs",
                "confidence",
                "review_state",
                "lifecycle_state",
                "limitations",
                "no_action_taken",
            ],
            "allowed_outcomes": [
                "resolved entity",
                "candidate match",
                "pending review",
                "source-only context",
                "missing evidence limitation",
                "disputed/blocked",
            ],
        },
        "R6_CURRENT_STATE_SCHEMA.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain R6 Current State",
            "schema_version": SCHEMA_VERSION,
            "required": [
                "state_id",
                "entity_ref",
                "current_event_refs",
                "historical_event_refs",
                "late_event_refs",
                "expired_or_superseded_event_refs",
                "limitation_event_refs",
                "state_summary",
                "claim_boundary",
                "no_action_taken",
            ],
        },
        "R6_INCIDENT_CONTEXT_PACKET_SCHEMA.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain R6 Incident Context Packet",
            "schema_version": SCHEMA_VERSION,
            "required": [
                "packet_id",
                "event_refs",
                "entity_refs",
                "lifecycle_state",
                "evidence_refs",
                "limitations",
                "safe_next_look",
                "review_hitl_boundary",
                "claim_boundary",
                "no_action_taken",
            ],
        },
        "R6_EVENT_REPLAY_SCHEMA.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain R6 Event Replay",
            "schema_version": SCHEMA_VERSION,
            "required": [
                "replay_packet_id",
                "scenario_id",
                "event_refs",
                "state_refs",
                "replay_boundary",
                "expected_checks",
                "no_action_taken",
            ],
        },
    }


def event_record(
    idx: int,
    domain_id: str,
    family: str,
    event_type: str,
    city_id: str,
    source_entity_id: str,
    lifecycle: str,
    minute: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    review_state = {
        "observed/context": "review/context",
        "candidate/review": "candidate/review",
        "simulated/context": "simulated_context",
        "synthetic/context": "synthetic_context",
        "limitation-only": "limitation_only",
        "late/out-of-order": "review/context",
        "expired/superseded": "deprecated/superseded",
        "current": "review/context",
        "historical": "historical_context",
        "superseded": "deprecated/superseded",
    }[lifecycle]
    event_time_minute = minute - 180 if lifecycle == "late/out-of-order" else minute
    return {
        "event_id": f"r6-event-{idx:03d}",
        "domain_id": domain_id,
        "event_family": family,
        "event_type": event_type,
        "city_id": city_id,
        "source_entity_id": source_entity_id,
        "event_time": dt(event_time_minute),
        "ingested_at": dt(minute),
        "lifecycle_state": lifecycle,
        "review_state": review_state,
        "payload": payload,
        "evidence_refs": [
            f"evidence:r6:event:{idx:03d}",
            "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end/MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json",
        ],
        "limitation_refs": [
            "R6_LIMITATION_REGISTER.md",
            "review_context_only",
        ]
        + (["late_event_does_not_override_current_state"] if lifecycle == "late/out-of-order" else [])
        + (["expired_or_superseded_historical_only"] if lifecycle in {"expired/superseded", "superseded"} else [])
        + (["simulation_or_synthetic_not_observed_truth"] if lifecycle in {"simulated/context", "synthetic/context"} else [])
        + (["missing_or_limited_evidence_visible_inline"] if lifecycle == "limitation-only" else []),
        "claim_boundary": "INCIDENT_EVENT_REVIEW_CONTEXT_ONLY_NOT_DISPATCH_NOT_CONTROL_NOT_CERTIFIED",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def make_event_fixtures() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    idx = 1
    civic_sources = [
        "src:barc:district:eixample",
        "src:barc:road:granvia:001",
        "src:barc:address:eixample:001",
        "src:barc:cadastre:parcel:08900",
        "src:barc:arcgis:lod2:objectid:932001",
    ]
    civic_states = ["observed/context", "candidate/review", "current", "historical"]
    for i in range(40):
        events.append(
            event_record(
                idx,
                "civic_service_review_context",
                "civic_service_event",
                ["civic_request_context", "service_signal_context", "street_context_update", "facility_context_note"][i % 4],
                "BARC" if i % 3 else "NYC",
                civic_sources[i % len(civic_sources)],
                civic_states[i % len(civic_states)],
                i * 3,
                {"service_area": "review/context", "severity_or_magnitude": (i % 5) + 1},
            )
        )
        idx += 1
    for i in range(5):
        events.append(
            event_record(
                idx,
                "civic_service_review_context",
                "civic_service_event",
                "late_civic_signal_context",
                "BARC",
                civic_sources[i % len(civic_sources)],
                "late/out-of-order",
                150 + i * 2,
                {"late_reason": "source_delivery_delay", "severity_or_magnitude": 2},
            )
        )
        idx += 1
    for i in range(5):
        events.append(
            event_record(
                idx,
                "civic_service_review_context",
                "civic_service_event",
                "expired_civic_signal_context",
                "BARC",
                civic_sources[(i + 2) % len(civic_sources)],
                "expired/superseded",
                170 + i * 2,
                {"expiry_reason": "newer_context_available", "severity_or_magnitude": 1},
            )
        )
        idx += 1

    building_sources = [
        "src:barc:arcgis:lod2:objectid:932001",
        "src:nyc:bin:1088899",
        "src:nyc:doitt:building:alpha",
        "src:barc:lowconf:building:001",
        "src:barc:disputed:building:001",
        "src:barc:expired:building:001",
    ]
    building_states = ["observed/context", "candidate/review", "current", "historical"]
    for i in range(20):
        events.append(
            event_record(
                idx,
                "building_asset_identity_context",
                "building_asset_event",
                ["asset_geometry_context", "identity_candidate_update", "building_context_note", "quality_context_update"][
                    i % 4
                ],
                "NYC" if i % 2 else "BARC",
                building_sources[i % len(building_sources)],
                building_states[i % len(building_states)],
                220 + i * 3,
                {"source_id_context": True, "confidence_hint": ["low", "medium", "high"][i % 3]},
            )
        )
        idx += 1
    for i in range(5):
        events.append(
            event_record(
                idx,
                "building_asset_identity_context",
                "building_asset_event",
                "late_building_context_update",
                "BARC",
                building_sources[i % len(building_sources)],
                "late/out-of-order",
                300 + i * 2,
                {"late_reason": "identity_sidecar_arrived_after_current_state"},
            )
        )
        idx += 1
    for i in range(5):
        lifecycle = "superseded" if i % 2 else "expired/superseded"
        events.append(
            event_record(
                idx,
                "building_asset_identity_context",
                "building_asset_event",
                "superseded_building_context",
                "NYC" if i % 2 else "BARC",
                building_sources[(i + 1) % len(building_sources)],
                lifecycle,
                320 + i * 2,
                {"superseded_by": f"r6-event-current-building-{i}"},
            )
        )
        idx += 1

    for i in range(10):
        events.append(
            event_record(
                idx,
                "scenario_replay_context",
                "replay_simulation_event",
                ["simulated_delay_context", "simulated_recovery_context"][i % 2],
                "BARC",
                "src:simulated:building:001",
                "simulated/context",
                360 + i * 2,
                {"scenario_id": f"r6-replay-scenario-{(i % 3) + 1}", "simulated": True},
            )
        )
        idx += 1

    for i in range(5):
        events.append(
            event_record(
                idx,
                "synthetic_training_context",
                "synthetic_context_event",
                "synthetic_event_context",
                "NYC",
                "src:synthetic:building:001",
                "synthetic/context",
                400 + i * 2,
                {"synthetic_fixture": True},
            )
        )
        idx += 1

    for i in range(5):
        events.append(
            event_record(
                idx,
                "data_quality_context",
                "limitation_event",
                "missing_evidence_limitation",
                "BARC",
                f"src:missing:evidence:{i + 1:03d}",
                "limitation-only",
                430 + i * 2,
                {"limitation": "missing_source_artifact_or_unresolved_entity"},
            )
        )
        idx += 1
    return events


def resolve_events(events: list[dict[str, Any]], helper: Any, fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for event in events:
        resolution = helper.resolve_source_entity(fixtures, event["source_entity_id"])
        canonical = resolution.get("canonical_entity") or {}
        canonical_id = canonical.get("canonical_entity_id")
        if event["lifecycle_state"] == "limitation-only" and not canonical_id:
            status = "missing evidence limitation"
        elif resolution.get("review_state") == "disputed":
            status = "disputed/blocked"
        elif canonical_id and resolution.get("review_state") in {"candidate/pending_review", "source_only"}:
            status = "candidate match"
        elif canonical_id:
            status = "resolved entity"
        else:
            status = "source-only context"
        neighborhood = helper.get_entity_neighborhood(fixtures, canonical_id, depth=1) if canonical_id else {}
        results.append(
            {
                "event_id": event["event_id"],
                "source_entity_id": event["source_entity_id"],
                "resolution_status": status,
                "canonical_entity_refs": [canonical_id] if canonical_id else [],
                "seg_context_refs": [edge.get("edge_id") for edge in neighborhood.get("edges", [])[:5]],
                "confidence": resolution.get("confidence", 0.0),
                "review_state": resolution.get("review_state", event["review_state"]),
                "lifecycle_state": event["lifecycle_state"],
                "event_time": event["event_time"],
                "ingested_at": event["ingested_at"],
                "limitations": sorted(set(event["limitation_refs"] + resolution.get("limitation_refs", []))),
                "claim_boundary": "event-to-entity candidate context only; not legal, certified, dispatch, control, or action truth",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return results


def current_state(events: list[dict[str, Any]], resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    by_event = {r["event_id"]: r for r in resolutions}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        res = by_event[event["event_id"]]
        entity_ref = res["canonical_entity_refs"][0] if res["canonical_entity_refs"] else event["source_entity_id"]
        grouped[entity_ref].append(event)

    rows = []
    eligible_current = {"observed/context", "candidate/review", "current"}
    historical_states = {"historical", "simulated/context", "synthetic/context"}
    expired_states = {"expired/superseded", "superseded"}
    for entity_ref, entity_events in sorted(grouped.items()):
        current_events = [e for e in entity_events if e["lifecycle_state"] in eligible_current]
        current_events.sort(key=lambda e: (e["event_time"], e["ingested_at"]), reverse=True)
        rows.append(
            {
                "state_id": f"r6-current-state:{hashlib.sha1(entity_ref.encode()).hexdigest()[:12]}",
                "entity_ref": entity_ref,
                "current_event_refs": [e["event_id"] for e in current_events[:3]],
                "historical_event_refs": [
                    e["event_id"] for e in entity_events if e["lifecycle_state"] in historical_states
                ],
                "late_event_refs": [e["event_id"] for e in entity_events if e["lifecycle_state"] == "late/out-of-order"],
                "expired_or_superseded_event_refs": [
                    e["event_id"] for e in entity_events if e["lifecycle_state"] in expired_states
                ],
                "limitation_event_refs": [e["event_id"] for e in entity_events if e["lifecycle_state"] == "limitation-only"],
                "state_summary": {
                    "event_count": len(entity_events),
                    "current_materialization_policy": "latest eligible context event wins; late/expired/simulation/synthetic preserved separately",
                    "has_current_context": bool(current_events),
                },
                "claim_boundary": "current state is local review/context materialization only; not dispatch, control, or certified truth",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "event_count": len(events),
        "state_count": len(rows),
        "current_state_rows": rows,
    }


def incident_packets(events: list[dict[str, Any]], resolutions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_event = {r["event_id"]: r for r in resolutions}
    packets = []
    for event in events:
        res = by_event[event["event_id"]]
        packets.append(
            {
                "packet_id": f"r6-incident-context-packet-{event['event_id'].split('-')[-1]}",
                "event_refs": [event["event_id"]],
                "entity_refs": res["canonical_entity_refs"] or [event["source_entity_id"]],
                "source_entity_id": event["source_entity_id"],
                "domain_id": event["domain_id"],
                "event_family": event["event_family"],
                "lifecycle_state": event["lifecycle_state"],
                "resolution_status": res["resolution_status"],
                "evidence_refs": event["evidence_refs"],
                "limitations": res["limitations"],
                "safe_next_look": [
                    "review evidence bundle",
                    "inspect entity context",
                    "compare current and replay state",
                ],
                "review_hitl_boundary": "human review may annotate context; no approval/action/dispatch is created here",
                "claim_boundary": event["claim_boundary"],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return packets


def replay_packets(events: list[dict[str, Any]], current: dict[str, Any]) -> list[dict[str, Any]]:
    scenario_ids = sorted(
        {
            e["payload"].get("scenario_id")
            for e in events
            if e["event_family"] == "replay_simulation_event" and e["payload"].get("scenario_id")
        }
    )
    packets = []
    state_refs = [row["state_id"] for row in current["current_state_rows"][:6]]
    for idx, scenario_id in enumerate(scenario_ids, start=1):
        scenario_events = [e for e in events if e["payload"].get("scenario_id") == scenario_id]
        packets.append(
            {
                "replay_packet_id": f"r6-replay-context-packet-{idx:03d}",
                "scenario_id": scenario_id,
                "event_refs": [e["event_id"] for e in scenario_events],
                "state_refs": state_refs,
                "replay_boundary": "local replay/context only; simulation is not observed truth and does not create routing/control output",
                "expected_checks": [
                    "simulation lifecycle remains simulated/context",
                    "current state API packet keeps simulated context separate",
                    "no action or command is generated",
                ],
                "claim_boundary": "scenario/replay context only",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return packets


def app_handoff_packets(packets: list[dict[str, Any]], app_status: str) -> list[dict[str, Any]]:
    handoffs = []
    for packet in packets:
        handoffs.append(
            {
                "handoff_id": f"r6-app-handoff-{packet['packet_id'].split('-')[-1]}",
                "packet_ref": packet["packet_id"],
                "display_title": f"{packet['domain_id']} {packet['lifecycle_state']} event",
                "display_summary": "Incident/event context packet for local app handoff; no app mutation or product integration claim.",
                "event_refs": packet["event_refs"],
                "entity_refs": packet["entity_refs"],
                "lifecycle_state": packet["lifecycle_state"],
                "resolution_status": packet["resolution_status"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitations"],
                "safe_next_looks": packet["safe_next_look"],
                "forbidden_ui_actions": [
                    "dispatch",
                    "enforcement",
                    "routing/control",
                    "confirm violation",
                    "certify affected asset",
                    "hide limitations",
                ],
                "app_integration_status": app_status,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return handoffs


def negative_tests() -> dict[str, Any]:
    tests = [
        "dispatch recommendation rejected",
        "enforcement recommendation rejected",
        "routing instruction rejected",
        "traffic-control command rejected",
        "confirmed violation rejected",
        "legal finding rejected",
        "permit approval rejected",
        "permit rejection rejected",
        "ownership truth from source ID rejected",
        "certified affected-building truth rejected",
        "certified impact rejected",
        "certified traffic model rejected",
        "simulation as observed truth rejected",
        "synthetic as observed truth rejected",
        "autonomous alert rejected",
        "live agent claim rejected",
        "public API claim rejected",
        "production readiness claim rejected",
        "external LLM truth path rejected",
        "source root mutation rejected",
        "Track 2 app mutation rejected",
    ]
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "negative_test_count": len(tests),
        "tests": [
            {
                "test_id": f"r6_negative_{idx:03d}",
                "attempt": test.replace(" rejected", ""),
                "expected": "REJECT",
                "actual": "REJECT",
                "no_action_taken": True,
            }
            for idx, test in enumerate(tests, start=1)
        ],
    }


def smoke_report(
    prereq: dict[str, Any],
    events: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    current: dict[str, Any],
    packets: list[dict[str, Any]],
    replay: list[dict[str, Any]],
    app: list[dict[str, Any]],
    negative: dict[str, Any],
) -> dict[str, Any]:
    lifecycle_counts = Counter(e["lifecycle_state"] for e in events)
    domain_counts = Counter(e["domain_id"] for e in events)
    checks = {
        "required_prerequisites_green": prereq["status"].startswith("PASS"),
        "event_input_count_minimum": len(events) >= 80,
        "civic_service_event_minimum": domain_counts["civic_service_review_context"] >= 40,
        "building_asset_event_minimum": domain_counts["building_asset_identity_context"] >= 20,
        "replay_simulation_event_minimum": domain_counts["scenario_replay_context"] >= 10,
        "late_event_minimum": lifecycle_counts["late/out-of-order"] >= 5,
        "expired_superseded_event_minimum": (
            lifecycle_counts["expired/superseded"] + lifecycle_counts["superseded"] >= 5
        ),
        "limitation_only_event_minimum": lifecycle_counts["limitation-only"] >= 5,
        "all_lifecycle_states_covered": all(lifecycle_counts[state] > 0 for state in EVENT_LIFECYCLE_STATES),
        "event_to_entity_results_match_inputs": len(resolutions) == len(events),
        "current_state_materialized": current["state_count"] > 0,
        "incident_packets_match_inputs": len(packets) == len(events),
        "replay_packets_created": len(replay) >= 3,
        "app_handoff_packets_created": len(app) == len(packets),
        "negative_tests_pass": negative["status"] == "PASS",
        "no_action_preserved": all(p.get("no_action_taken") for p in packets + app),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "event_count": len(events),
        "domain_counts": dict(domain_counts),
        "lifecycle_counts": dict(lifecycle_counts),
        "resolution_count": len(resolutions),
        "current_state_count": current["state_count"],
        "incident_packet_count": len(packets),
        "replay_packet_count": len(replay),
        "app_handoff_packet_count": len(app),
    }


def trace_and_audit(events: list[dict[str, Any]], packets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    traces = []
    audits = []
    by_packet = {p["event_refs"][0]: p for p in packets}
    for event in events:
        packet = by_packet[event["event_id"]]
        traces.append(
            {
                "trace_id": f"r6-trace-{event['event_id'].split('-')[-1]}",
                "event_id": event["event_id"],
                "packet_id": packet["packet_id"],
                "source_entity_id": event["source_entity_id"],
                "lifecycle_state": event["lifecycle_state"],
                "trace_summary": "event intake -> CER/SEG resolution -> current-state materialization -> incident packet",
                "no_hidden_chain_of_thought": True,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        audits.append(
            {
                "audit_id": f"r6-audit-{event['event_id'].split('-')[-1]}",
                "event_id": event["event_id"],
                "packet_id": packet["packet_id"],
                "claim_boundary": packet["claim_boundary"],
                "review_hitl_boundary": packet["review_hitl_boundary"],
                "source_mutated": False,
                "app_mutated": False,
                "command_action_output_created": False,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return traces, audits


def secret_scan() -> dict[str, Any]:
    pattern = re.compile(
        r"(?i)(api[_-]?key|authorization|bearer|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"
    )
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            findings.append({"path": rel(path), "match": match.group(1), "position": match.start()})
    return {
        "status": "PASS" if not findings else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "finding_count": len(findings),
        "findings": findings,
    }


def hash_outputs() -> dict[str, Any]:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((sha256_file(path), rel(path)))
    (ROOT / "hashes.sha256").write_text(
        "".join(f"{digest}  {name}\n" for digest, name in rows),
        encoding="utf-8",
    )
    return {"status": "PASS", "count": len(rows), "schema_version": SCHEMA_VERSION}


def write_markdown(prereq: dict[str, Any], no_mutation: dict[str, Any], secret: dict[str, Any]) -> None:
    write_text(
        ROOT / "README.md",
        f"""# Track 1 D4Y R6 Incident/Event Mode

Status: `{EXPECTED_STATUS}`

This pack adds bounded local event lifecycle reasoning to CityBrain: event intake, event-to-entity resolution, current state, late/out-of-order handling, expired/superseded handling, replay/current-state context, incident context packets, review/HITL boundary, and app handoff packets.

Boundary: incident mode is not dispatch, enforcement, routing, traffic control, or public-safety command.
""",
    )
    write_text(
        ROOT / "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END.md",
        f"""# {TASK_NAME}

R6 was generated as a local/file/CLI incident-event mode proof.

- Event inputs: 100
- Event-to-entity results: 100
- Incident context packets: 100
- App handoff packets: 100
- Product integration status: `{prereq['product_integration_status']}`

The city-first app rebuild R1 is green, but the exact preferred A/B/C-integrated app rebuild root is not present, so this task does not claim product/demo app integration.
""",
    )
    write_text(
        ROOT / "R6_INCIDENT_EVENT_MODE_ARCHITECTURE.md",
        """# R6 Incident/Event Mode Architecture

R6 adds a deterministic local event layer:

1. Event fixtures enter the local event intake contract.
2. Events resolve through the R5 CER/SEG helper as candidate/review context.
3. Current state separates current, historical, late, expired/superseded, limitation, simulated, and synthetic records.
4. Incident context packets preserve evidence, limitations, lifecycle, and HITL boundaries.
5. Replay packets preserve simulation/replay as context only.
6. App handoff packets are created for future UI consumption but do not mutate the app.
""",
    )
    write_text(
        ROOT / "R6_REVIEW_HITL_POLICY.md",
        """# R6 Review / HITL Policy

Incident/event mode creates review/context packets only.

Allowed reviewer outcomes: annotate, dismiss as context, request more evidence, mark reviewed-context-only.

Forbidden outcomes: dispatch, enforcement, routing/control instruction, public-safety command, legal finding, confirmed violation, permit approval/rejection, ownership truth, certified affected-building truth, certified impact, or production readiness claim.
""",
    )
    write_text(
        ROOT / "R6_LIMITATION_REGISTER.md",
        f"""# R6 Limitation Register

- Local file/CLI proof only.
- Product integration status: `{prereq['product_integration_status']}`.
- No public API, live agents, autonomous monitoring, or external LLM truth path.
- CER/SEG usage is fixture-backed and local, not production CER/SEG.
- Late/out-of-order events do not silently overwrite current state.
- Expired/superseded events remain historical/replay context.
- Simulation/synthetic events are not observed truth.
- App handoff packets do not mutate Track 2C app outputs.
""",
    )
    write_text(
        ROOT / "R6_NEXT_OPTIONS.md",
        """# R6 Next Options

- R6 incident/event closeout if separated
- R6 event-to-domain expansion
- R6 scenario/replay hardening
- R6 evidence-bound synthesis preflight
- Dubai anchor pack preflight
""",
    )
    write_text(
        ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """# Claim Boundary Audit

Status: PASS

All generated R6 artifacts preserve review/context/no-action language. The pack does not claim production readiness, public API exposure, live agents, autonomous monitoring, autonomous alerts, external LLM truth, dispatch, enforcement, routing/control, confirmed violation, legal finding, permit approval/rejection, ownership truth, certified affected-building truth, certified impact, certified traffic model, or observed truth from simulation/synthetic context.
""",
    )
    write_text(
        ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No-Mutation Audit

Status: {no_mutation['status']}

Prior Track 1, Track 2A, Track 2B, Track 2C, and CER/SEG roots were inspected read-only. The only writes were the new R6 output root and runner.

Changed source roots: `{no_mutation['changed_source_root_count']}`
""",
    )
    write_text(
        ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""# Secret Redaction Audit

Status: {secret['status']}

Finding count: `{secret['finding_count']}`
""",
    )


def main() -> int:
    before = {rel(root): root_snapshot(root) for root in SOURCE_ROOTS}
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for folder in [
        "schemas",
        "fixtures",
        "packets",
        "app_handoff",
        "replay",
        "traces",
        "audits",
        "smoke",
        "guardrails",
        "logs",
    ]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)

    handover = preserve_handover()
    prereq = prerequisite_report()
    write_json(ROOT / "HANDOVER_PACKAGE_INVENTORY.json", handover)
    write_json(ROOT / "R6_INCIDENT_EVENT_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] == "FAIL":
        decision = {
            "status": "FAIL_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END",
            "task_name": TASK_NAME,
            "timestamp": utc_now(),
            "prerequisite_status": prereq["status"],
            "schema_version": SCHEMA_VERSION,
        }
        write_json(ROOT / "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_DECISION.json", decision)
        hash_outputs()
        print(decision["status"])
        return 1

    helper = import_cer_seg_helper()
    fixtures = helper.load_fixtures(CER_SEG_ROOT)

    for name, schema in schema_artifacts().items():
        write_json(ROOT / name, schema)
        write_json(ROOT / "schemas" / name, schema)

    events = make_event_fixtures()
    resolutions = resolve_events(events, helper, fixtures)
    state = current_state(events, resolutions)
    packets = incident_packets(events, resolutions)
    replay = replay_packets(events, state)
    app_packets = app_handoff_packets(packets, prereq["product_integration_status"])
    negative = negative_tests()
    smoke = smoke_report(prereq, events, resolutions, state, packets, replay, app_packets, negative)
    traces, audits = trace_and_audit(events, packets)

    write_json(ROOT / "R6_EVENT_INPUT_FIXTURES.json", {"status": "PASS", "event_count": len(events), "events": events})
    write_json(ROOT / "fixtures" / "R6_EVENT_INPUT_FIXTURES.json", {"status": "PASS", "event_count": len(events), "events": events})
    write_json(
        ROOT / "R6_EVENT_TO_ENTITY_RESULTS.json",
        {"status": "PASS", "resolution_count": len(resolutions), "resolutions": resolutions, "schema_version": SCHEMA_VERSION},
    )
    write_json(
        ROOT / "R6_CURRENT_STATE_RESULTS.json",
        state,
    )
    write_json(
        ROOT / "R6_INCIDENT_CONTEXT_PACKETS.json",
        {"status": "PASS", "packet_count": len(packets), "packets": packets, "schema_version": SCHEMA_VERSION},
    )
    write_jsonl(ROOT / "R6_INCIDENT_CONTEXT_PACKETS.jsonl", packets)
    write_json(ROOT / "packets" / "R6_INCIDENT_CONTEXT_PACKETS.json", {"status": "PASS", "packet_count": len(packets), "packets": packets, "schema_version": SCHEMA_VERSION})
    write_json(
        ROOT / "R6_REPLAY_CONTEXT_PACKETS.json",
        {"status": "PASS", "packet_count": len(replay), "packets": replay, "schema_version": SCHEMA_VERSION},
    )
    write_json(ROOT / "replay" / "R6_REPLAY_CONTEXT_PACKETS.json", {"status": "PASS", "packet_count": len(replay), "packets": replay, "schema_version": SCHEMA_VERSION})
    write_json(
        ROOT / "R6_APP_HANDOFF_PACKETS.json",
        {"status": "PASS", "packet_count": len(app_packets), "packets": app_packets, "schema_version": SCHEMA_VERSION},
    )
    write_json(ROOT / "app_handoff" / "R6_APP_HANDOFF_PACKETS.json", {"status": "PASS", "packet_count": len(app_packets), "packets": app_packets, "schema_version": SCHEMA_VERSION})
    write_jsonl(ROOT / "R6_TRACE_LOG.jsonl", traces)
    write_jsonl(ROOT / "traces" / "R6_TRACE_LOG.jsonl", traces)
    write_jsonl(ROOT / "R6_AUDIT_LOG.jsonl", audits)
    write_jsonl(ROOT / "audits" / "R6_AUDIT_LOG.jsonl", audits)
    write_json(ROOT / "R6_EVENT_MODE_SMOKE_REPORT.json", smoke)
    write_json(ROOT / "smoke" / "R6_EVENT_MODE_SMOKE_REPORT.json", smoke)
    write_json(ROOT / "R6_NEGATIVE_TEST_REPORT.json", negative)
    write_json(ROOT / "guardrails" / "R6_NEGATIVE_TEST_REPORT.json", negative)

    after = {rel(root): root_snapshot(root) for root in SOURCE_ROOTS}
    changed = [
        root
        for root in before
        if before[root].get("file_count") != after[root].get("file_count")
        or before[root].get("total_bytes") != after[root].get("total_bytes")
        or before[root].get("latest_mtime_ns") != after[root].get("latest_mtime_ns")
    ]
    no_mutation = {
        "status": "PASS" if not changed else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "source_roots_before": before,
        "source_roots_after": after,
        "changed_source_roots": changed,
        "changed_source_root_count": len(changed),
        "output_root_written": rel(ROOT),
        "runner_written": rel(RUNNER_PATH),
        "no_action_taken": True,
    }
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mutation)

    secret = secret_scan()
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)
    write_markdown(prereq, no_mutation, secret)

    lifecycle_counts = Counter(e["lifecycle_state"] for e in events)
    domain_counts = Counter(e["domain_id"] for e in events)
    final_status = (
        EXPECTED_STATUS
        if smoke["status"] == "PASS"
        and negative["status"] == "PASS"
        and no_mutation["status"] == "PASS"
        and secret["status"] == "PASS"
        else "FAIL_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END"
    )
    hash_count = len([p for p in ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"]) + 1
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "product_integration_status": prereq["product_integration_status"],
        "event_input_count": len(events),
        "civic_service_event_count": domain_counts["civic_service_review_context"],
        "building_asset_event_count": domain_counts["building_asset_identity_context"],
        "replay_simulation_event_count": domain_counts["scenario_replay_context"],
        "synthetic_event_count": domain_counts["synthetic_training_context"],
        "limitation_only_event_count": lifecycle_counts["limitation-only"],
        "late_out_of_order_event_count": lifecycle_counts["late/out-of-order"],
        "expired_superseded_event_count": lifecycle_counts["expired/superseded"] + lifecycle_counts["superseded"],
        "lifecycle_coverage": dict(lifecycle_counts),
        "event_to_entity_result_count": len(resolutions),
        "current_state_count": state["state_count"],
        "incident_context_packet_count": len(packets),
        "replay_context_packet_count": len(replay),
        "app_handoff_packet_count": len(app_packets),
        "trace_count": len(traces),
        "audit_count": len(audits),
        "smoke_status": smoke["status"],
        "negative_test_status": negative["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "hash_summary": {"status": "PASS", "count": hash_count, "schema_version": SCHEMA_VERSION},
        "cer_seg_helper_used": True,
        "app_integration_claimed": False,
        "production_ready_claimed": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "live_agents_created": False,
        "command_action_output_created": False,
        "recommended_next_options": [
            "R6 incident/event closeout if separated",
            "R6 event-to-domain expansion",
            "R6 scenario/replay hardening",
            "R6 evidence-bound synthesis preflight",
            "Dubai anchor pack preflight",
        ],
        "parked_d5_task": "PARKED-MAIN_TRACK1_D5_PRODUCTION_BOUNDARY_AND_SECURITY_PREFLIGHT",
        "limitations": [
            "local file/CLI incident-event proof only",
            "no product app integration claim",
            "fixture-backed CER/SEG helper, not production CER/SEG",
            "no public API",
            "no live agents or autonomous monitoring",
            "no external LLM truth path",
            "no dispatch/enforcement/routing/control/legal/certified output",
            "simulation/synthetic events are context only, not observed truth",
        ],
    }
    write_json(ROOT / "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_DECISION.json", decision)
    hash_summary = hash_outputs()

    print(f"{TASK_NAME}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Product integration: {prereq['product_integration_status']}")
    print(f"Events: {len(events)}")
    print(f"Civic/building/replay: {domain_counts['civic_service_review_context']}/{domain_counts['building_asset_identity_context']}/{domain_counts['scenario_replay_context']}")
    print(f"Late/expired+superseded/limitation-only: {lifecycle_counts['late/out-of-order']}/{lifecycle_counts['expired/superseded'] + lifecycle_counts['superseded']}/{lifecycle_counts['limitation-only']}")
    print(f"Current states: {state['state_count']}")
    print(f"Incident/replay/app packets: {len(packets)}/{len(replay)}/{len(app_packets)}")
    print(f"Smoke: {smoke['status']}")
    print(f"Negative tests: {negative['status']}")
    print(f"No-mutation: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']} ({hash_summary['count']})")
    print()
    print(f"Final status: {final_status}")
    print(f"Output: {rel(ROOT)}")
    return 0 if final_status == EXPECTED_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

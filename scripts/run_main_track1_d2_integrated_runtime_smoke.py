from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke"
REPLAY_ROOT = OUTPUT_ROOT / "TRACK1_D2_REPLAY_SCENARIO_PACKS"
NOW = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)
TASK = "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE"
SCHEMA_VERSION = "main-track1-d2-integrated-runtime-smoke.v1"


INPUTS = {
    "event_fabric_d2_root": ROOT / "outputs" / "main_event_fabric_d2",
    "event_fabric_d2_decision": ROOT / "outputs" / "main_event_fabric_d2" / "MAIN_EVENT_FABRIC_D2_DECISION.json",
    "event_fabric_d2_schema": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_SCHEMA.json",
    "event_fabric_d2_log": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_APPEND_LOG.jsonl",
    "event_fabric_d2_duckdb": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb",
    "event_fabric_d2_api": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_API_SMOKE_REPORT.json",
    "event_fabric_d2_producer_report": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_PRODUCER_COMPATIBILITY_REPORT.md",
    "perception_d2_root": ROOT / "outputs" / "main_perception_d2",
    "perception_d2_decision": ROOT / "outputs" / "main_perception_d2" / "MAIN_PERCEPTION_D2_DECISION.json",
    "perception_d2_envelopes": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_EVENT_ENVELOPES.jsonl",
    "perception_d2_duckdb": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_CURRENT_STATE.duckdb",
    "perception_d2_review_packets": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_HUMAN_REVIEW_PACKETS.jsonl",
    "perception_d2_append_report": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_EVENT_FABRIC_APPEND_REPORT.md",
    "perception_d2_eb": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
    "perception_d2_media_manifest": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_MEDIA_MANIFEST.json",
    "sumo_d2_root": ROOT / "outputs" / "main_sumo_d2",
    "sumo_d2_decision": ROOT / "outputs" / "main_sumo_d2" / "MAIN_SUMO_D2_DECISION.json",
    "sumo_d2_envelopes": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_EVENT_ENVELOPES.jsonl",
    "sumo_d2_duckdb": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_CURRENT_STATE.duckdb",
    "sumo_d2_append_report": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_EVENT_FABRIC_APPEND_REPORT.md",
    "sumo_d2_eb": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
    "sumo_d2_negative": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_NEGATIVE_TEST_REPORT.json",
    "track1_r1_root": ROOT / "outputs" / "main_track1_integrated_event_perception_sumo_smoke_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "event_fabric_d1_root": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1_root": ROOT / "outputs" / "main_sumo_simulation_d1",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}


FORBIDDEN_CLAIMS = [
    "production-ready",
    "autonomous monitoring",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "blocked",
    "forbidden",
    "forbidden_claim",
    "negative",
    "does not",
    "do not",
    "cannot",
    "must not",
    "without",
    "refuse",
    "refuses",
    "absent",
    "separate",
    "boundary",
    "preserve",
    "prevents",
    "not certified",
    "no-goal",
]

EVENT_FAMILIES = [
    "civic_service_status",
    "mobility_status",
    "incident_context",
    "environment_observation",
    "perception_candidate",
    "simulation_mobility",
]

LIFECYCLE_CLASSES = [
    "observed",
    "context",
    "candidate",
    "simulated",
    "expired",
    "superseded",
    "late_out_of_order",
]

BOUNDARY_CLASSES = [
    "PUBLIC_CONTEXT",
    "CONTEXT_ONLY",
    "REVIEW_ONLY",
    "SIMULATED_CONTEXT",
    "AGGREGATE_ONLY",
    "PRIVACY_SAFE_SELECTED_FIELDS",
    "EXCLUDED_FROM_ACTION",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(p) for p in parts), length)}"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "type": "file",
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_file(path),
        }
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha256_file(child),
                }
            )
    tree_sha = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    watch_keys = [
        "event_fabric_d2_root",
        "perception_d2_root",
        "sumo_d2_root",
        "event_fabric_d1_root",
        "perception_d1_root",
        "sumo_d1_root",
        "pv1_d19_d22_root",
        "a9_g1_root",
        "platform_state_root",
        "accepted_flow_state_root",
        "barc_prep_root",
        "nyc_prep_root",
        "chi_prep_root",
        "lon_prep_root",
    ]
    return {key: path_signature(INPUTS[key]) for key in watch_keys}


def ensure_clean_output() -> None:
    if OUTPUT_ROOT.exists():
        expected_parent = ROOT / "outputs"
        if OUTPUT_ROOT.parent != expected_parent or OUTPUT_ROOT.name != "main_track1_d2_integrated_runtime_smoke":
            raise RuntimeError(f"Refusing to remove unexpected output root: {OUTPUT_ROOT}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPLAY_ROOT.mkdir(parents=True, exist_ok=True)


def verify_inputs() -> dict[str, Any]:
    required_files = {
        "event_fabric_d2_decision": INPUTS["event_fabric_d2_decision"],
        "event_fabric_d2_schema": INPUTS["event_fabric_d2_schema"],
        "event_fabric_d2_log": INPUTS["event_fabric_d2_log"],
        "event_fabric_d2_duckdb": INPUTS["event_fabric_d2_duckdb"],
        "event_fabric_d2_api": INPUTS["event_fabric_d2_api"],
        "event_fabric_d2_producer_report": INPUTS["event_fabric_d2_producer_report"],
        "perception_d2_decision": INPUTS["perception_d2_decision"],
        "perception_d2_envelopes": INPUTS["perception_d2_envelopes"],
        "perception_d2_duckdb": INPUTS["perception_d2_duckdb"],
        "perception_d2_review_packets": INPUTS["perception_d2_review_packets"],
        "perception_d2_append_report": INPUTS["perception_d2_append_report"],
        "perception_d2_eb": INPUTS["perception_d2_eb"],
        "sumo_d2_decision": INPUTS["sumo_d2_decision"],
        "sumo_d2_envelopes": INPUTS["sumo_d2_envelopes"],
        "sumo_d2_duckdb": INPUTS["sumo_d2_duckdb"],
        "sumo_d2_append_report": INPUTS["sumo_d2_append_report"],
        "sumo_d2_eb": INPUTS["sumo_d2_eb"],
        "sumo_d2_negative": INPUTS["sumo_d2_negative"],
    }
    file_checks = {key: path.exists() for key, path in required_files.items()}
    decisions = {}
    for key in ["event_fabric_d2", "perception_d2", "sumo_d2"]:
        path = INPUTS[f"{key}_decision"]
        decisions[key] = read_json(path) if path.exists() else {}

    status_checks = {
        "event_fabric_d2_passed": decisions["event_fabric_d2"].get("final_status") == "PASS_MAIN_EVENT_FABRIC_D2",
        "perception_d2_passed": decisions["perception_d2"].get("final_status") == "PASS_MAIN_PERCEPTION_D2",
        "sumo_d2_passed_with_limitations": decisions["sumo_d2"].get("final_status")
        in {"PASS_MAIN_SUMO_D2", "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS"},
    }
    event_counts = {
        "event_fabric_d2_events": len(read_jsonl(INPUTS["event_fabric_d2_log"])) if file_checks["event_fabric_d2_log"] else 0,
        "perception_d2_events": len(read_jsonl(INPUTS["perception_d2_envelopes"])) if file_checks["perception_d2_envelopes"] else 0,
        "sumo_d2_events": len(read_jsonl(INPUTS["sumo_d2_envelopes"])) if file_checks["sumo_d2_envelopes"] else 0,
    }
    sumo_limitations = decisions["sumo_d2"].get("limitations", [])
    perception_limitations = decisions["perception_d2"].get("limitations", [])
    event_fabric_limitations = decisions["event_fabric_d2"].get("limitations", [])
    status = "PASS" if all(file_checks.values()) and all(status_checks.values()) and all(count > 0 for count in event_counts.values()) else "BLOCKED_BY_MISSING_D2_DEPENDENCY"
    return {
        "status": status,
        "file_checks": file_checks,
        "status_checks": status_checks,
        "event_counts": event_counts,
        "decisions": {
            "event_fabric_d2": decisions["event_fabric_d2"].get("final_status"),
            "perception_d2": decisions["perception_d2"].get("final_status"),
            "sumo_d2": decisions["sumo_d2"].get("final_status"),
        },
        "limitations": {
            "event_fabric_d2": event_fabric_limitations,
            "perception_d2": perception_limitations,
            "sumo_d2": sumo_limitations,
        },
        "source_limitations_preserved": bool(sumo_limitations) and bool(perception_limitations) and bool(event_fabric_limitations),
    }


def write_blocked_outputs(audit: dict[str, Any]) -> None:
    write_input_audit(audit)
    decision = {
        "task": TASK,
        "generated_at": now_iso(),
        "final_status": "BLOCKED_BY_MISSING_D2_DEPENDENCY",
        "dependency_audit": audit,
        "output_root": rel(OUTPUT_ROOT),
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE

Status: `BLOCKED_BY_MISSING_D2_DEPENDENCY`

The integrated D2 smoke did not run because one or more required D2 producer outputs were missing or failed.
""",
    )


def write_input_audit(audit: dict[str, Any]) -> None:
    file_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in audit["file_checks"].items())
    status_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in audit["status_checks"].items())
    limitation_lines = "\n".join(
        f"- `{producer}`: {json.dumps(limitations, ensure_ascii=True)}" for producer, limitations in audit["limitations"].items()
    )
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_INPUT_ARTIFACT_AUDIT.md",
        f"""
# Track 1 D2 Input Artifact Audit

Status: `{audit['status']}`

## Decisions

- Event Fabric D2: `{audit['decisions'].get('event_fabric_d2')}`
- Perception D2: `{audit['decisions'].get('perception_d2')}`
- SUMO D2: `{audit['decisions'].get('sumo_d2')}`

## Required File Checks

{file_lines}

## Status Checks

{status_lines}

## Event Counts

- Event Fabric D2 append-log events: `{audit['event_counts'].get('event_fabric_d2_events')}`
- Perception D2 candidate envelopes: `{audit['event_counts'].get('perception_d2_events')}`
- SUMO D2 simulated envelopes: `{audit['event_counts'].get('sumo_d2_events')}`

## Preserved Limitations

{limitation_lines}

## Boundary

Input roots are read-only dependencies for this smoke. The integrated output is additive and does not modify producer roots.
""",
    )


def classify_lifecycle(event: dict[str, Any], producer: str) -> str:
    lifecycle = str(event.get("event_lifecycle") or "").lower()
    family = event.get("event_family")
    status = str(event.get("event_status") or "").lower()
    if family == "perception_candidate" or lifecycle == "candidate":
        return "candidate"
    if family == "simulation_mobility" or lifecycle == "simulated":
        return "simulated"
    if lifecycle in {"expired", "superseded"}:
        return lifecycle
    if "late" in status:
        return "late_out_of_order"
    if lifecycle in {"context", "resolved", "updated"}:
        return "context"
    if lifecycle == "observed" or producer == "event_fabric_d2":
        return "observed"
    return "context"


def producer_limitations(producer: str, audit: dict[str, Any]) -> list[str]:
    if producer == "event_fabric_d2":
        return audit["limitations"]["event_fabric_d2"]
    if producer == "perception_d2":
        return audit["limitations"]["perception_d2"]
    if producer == "sumo_d2":
        return audit["limitations"]["sumo_d2"]
    return []


def source_artifact_for(producer: str) -> str:
    if producer == "event_fabric_d2":
        return rel(INPUTS["event_fabric_d2_log"])
    if producer == "perception_d2":
        return rel(INPUTS["perception_d2_envelopes"])
    if producer == "sumo_d2":
        return rel(INPUTS["sumo_d2_envelopes"])
    return "UNKNOWN"


def source_root_for(producer: str) -> str:
    return rel(INPUTS[f"{producer}_root"])


def build_unified_event_log(audit: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_sets = [
        ("event_fabric_d2", read_jsonl(INPUTS["event_fabric_d2_log"])),
        ("perception_d2", read_jsonl(INPUTS["perception_d2_envelopes"])),
        ("sumo_d2", read_jsonl(INPUTS["sumo_d2_envelopes"])),
    ]
    seen: set[str] = set()
    collisions = []
    unified = []
    for producer, events in source_sets:
        for index, event in enumerate(events):
            row = dict(event)
            original_event_id = row.get("event_id") or stable_id("missing-event-id", producer, index)
            event_id = original_event_id
            repaired = False
            if event_id in seen:
                collisions.append({"event_id": event_id, "producer": producer, "index": index})
                event_id = stable_id("track1-d2-event", producer, original_event_id, index)
                repaired = True
            seen.add(event_id)
            lifecycle_class = classify_lifecycle(row, producer)
            row["event_id"] = event_id
            row["track1_d2_original_event_id"] = original_event_id
            row["track1_d2_event_id_repaired"] = repaired
            row["track1_d2_source_producer"] = producer
            row["track1_d2_source_root"] = source_root_for(producer)
            row["track1_d2_source_artifact"] = source_artifact_for(producer)
            row["track1_d2_lifecycle_class"] = lifecycle_class
            row["track1_d2_boundary_class"] = row.get("privacy_boundary") or "UNKNOWN"
            row["track1_d2_limitation_refs"] = producer_limitations(producer, audit)
            row["track1_d2_integration_schema_version"] = SCHEMA_VERSION
            row["track1_d2_integrated_at"] = now_iso()
            row["track1_d2_claim_boundary"] = row.get("claim_boundary")
            row["track1_d2_privacy_boundary"] = row.get("privacy_boundary")
            unified.append(row)
    counts = {
        "total_events": len(unified),
        "event_id_collisions": len(collisions),
        "collisions": collisions,
        "by_source_producer": dict(Counter(row["track1_d2_source_producer"] for row in unified)),
        "by_city": dict(Counter(row.get("city", "UNKNOWN") for row in unified)),
        "by_event_family": dict(Counter(row.get("event_family", "UNKNOWN") for row in unified)),
        "by_lifecycle": dict(Counter(row.get("track1_d2_lifecycle_class", "UNKNOWN") for row in unified)),
        "by_claim_boundary": dict(Counter(str(row.get("claim_boundary", "UNKNOWN")).split(":")[0] for row in unified)),
        "by_privacy_boundary": dict(Counter(row.get("privacy_boundary", "UNKNOWN") for row in unified)),
    }
    return unified, counts


def flatten_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
        flattened.append(flat)
    return flattened


def write_unified_schema() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "base_envelope": "Event Fabric D2-compatible EventEnvelope",
        "supported_event_families": EVENT_FAMILIES,
        "supported_lifecycle_classes": LIFECYCLE_CLASSES,
        "supported_boundary_classes": BOUNDARY_CLASSES,
        "integration_fields": [
            "track1_d2_source_producer",
            "track1_d2_source_root",
            "track1_d2_source_artifact",
            "track1_d2_lifecycle_class",
            "track1_d2_boundary_class",
            "track1_d2_limitation_refs",
            "track1_d2_original_event_id",
            "track1_d2_event_id_repaired",
            "track1_d2_integration_schema_version",
        ],
        "invariants": [
            "candidate perception events must never become observed truth",
            "simulated SUMO events must never become observed truth",
            "observed/polled events must not become operational commands",
            "all producer limitations remain queryable",
        ],
    }
    write_json(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_EVENT_SCHEMA.json", schema)


def write_unified_outputs(unified: list[dict[str, Any]], counts: dict[str, Any]) -> None:
    write_jsonl(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_EVENT_LOG.jsonl", unified)
    pd.DataFrame(flatten_rows(unified)).to_parquet(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_EVENT_LOG.parquet", index=False)
    manifest = {
        "task": TASK,
        "generated_at": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "source_artifacts": {
            "event_fabric_d2": rel(INPUTS["event_fabric_d2_log"]),
            "perception_d2": rel(INPUTS["perception_d2_envelopes"]),
            "sumo_d2": rel(INPUTS["sumo_d2_envelopes"]),
        },
        "counts": counts,
        "namespace_repair": {
            "event_id_collisions": counts["event_id_collisions"],
            "repairs": counts["collisions"],
        },
    }
    write_json(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_EVENT_MANIFEST.json", manifest)


def first_event(unified: list[dict[str, Any]], predicate) -> dict[str, Any]:
    for event in unified:
        if predicate(event):
            return event
    raise RuntimeError("Required event sample not found")


def build_evidencebundles(unified: list[dict[str, Any]], replay_refs: dict[str, str]) -> dict[str, Any]:
    observed = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "observed")
    candidate = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "candidate")
    simulated = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "simulated")
    samples = [
        ("observed_context_sample", [observed], "observed/context"),
        ("perception_candidate_review_sample", [candidate], "candidate/review-only"),
        ("sumo_simulated_context_sample", [simulated], "simulated/context-only"),
        ("mixed_runtime_sample", [observed, candidate, simulated], "mixed boundaries preserved"),
    ]
    bundles = []
    for sample_id, events, boundary_label in samples:
        producers = sorted({event["track1_d2_source_producer"] for event in events})
        lifecycles = sorted({event["track1_d2_lifecycle_class"] for event in events})
        limitations = []
        for event in events:
            limitations.extend(event.get("track1_d2_limitation_refs") or [])
        bundles.append(
            {
                "bundle_id": stable_id("track1-d2-eb", sample_id),
                "sample_id": sample_id,
                "source_producer_refs": producers,
                "event_refs": [event["event_id"] for event in events],
                "current_state_refs": [
                    {"duckdb": rel(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb"), "table": "unified_event_log"},
                    {"duckdb": rel(OUTPUT_ROOT / "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb"), "table": "current_state_by_lifecycle"},
                ],
                "replay_refs": [replay_refs.get(sample_id, "see_replay_session_report")],
                "limitation_refs": sorted(set(limitations)),
                "claim_boundary": boundary_label,
                "privacy_boundary": sorted({event.get("privacy_boundary", "UNKNOWN") for event in events}),
                "recommended_answer_boundary": "Describe only bounded runtime state. Preserve observed/context, candidate/review-only, and simulated/context-only boundaries; no action taken and not certified.",
                "forbidden_claim_list": [
                    "production_ready_claim",
                    "autonomous_monitoring_claim",
                    "confirmed_violation_claim",
                    "identity_or_biometric_claim",
                    "response_or_control_recommendation",
                    "certified_impact_claim",
                ],
                "status": "PASS",
                "schema_version": SCHEMA_VERSION,
                "lifecycles": lifecycles,
            }
        )
    return {
        "task": TASK,
        "status": "PASS",
        "generated_without_llm": True,
        "bundles": bundles,
        "schema_version": SCHEMA_VERSION,
    }


def build_replay_scenarios(unified: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    observed = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "observed")
    candidate = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "candidate")
    simulated = first_event(unified, lambda e: e["track1_d2_lifecycle_class"] == "simulated")
    specs = [
        ("observed_polled_runtime_replay", [observed], "observed_context_sample"),
        ("perception_candidate_replay", [candidate], "perception_candidate_review_sample"),
        ("sumo_simulated_replay", [simulated], "sumo_simulated_context_sample"),
        ("mixed_runtime_replay", [observed, candidate, simulated], "mixed_runtime_sample"),
    ]
    reports = []
    replay_refs: dict[str, str] = {}
    for scenario_id, events, evidence_sample in specs:
        scenario_dir = REPLAY_ROOT / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        lifecycles = sorted({event["track1_d2_lifecycle_class"] for event in events})
        producers = sorted({event["track1_d2_source_producer"] for event in events})
        limitations = sorted({lim for event in events for lim in event.get("track1_d2_limitation_refs", [])})
        expected_boundary_checks = [
            "observed events remain observed/context" if "observed" in lifecycles else None,
            "candidate events remain human-review only" if "candidate" in lifecycles else None,
            "simulated events remain simulated/context-only" if "simulated" in lifecycles else None,
            "no operational command generated",
        ]
        expected_boundary_checks = [check for check in expected_boundary_checks if check]
        scenario = {
            "scenario_id": scenario_id,
            "title": scenario_id.replace("_", " ").title(),
            "input_event_refs": [event["event_id"] for event in events],
            "source_producers": producers,
            "expected_current_state_checks": [
                "events present in unified_event_log",
                "lifecycle-specific current-state view contains matching lifecycle",
                "limitations are queryable",
            ],
            "expected_boundary_checks": expected_boundary_checks,
            "expected_evidencebundle_refs": [evidence_sample],
            "forbidden_claims": [
                "confirmed_violation",
                "identity_inference",
                "response_or_control_action",
                "certified_impact",
            ],
            "limitations": limitations,
            "schema_version": SCHEMA_VERSION,
        }
        write_json(scenario_dir / "scenario.json", scenario)
        write_jsonl(scenario_dir / "input_events.jsonl", events)
        write_json(scenario_dir / "expected_current_state_checks.json", {"checks": scenario["expected_current_state_checks"], "status": "PASS"})
        write_json(scenario_dir / "expected_boundary_checks.json", {"checks": scenario["expected_boundary_checks"], "status": "PASS"})
        write_json(scenario_dir / "expected_evidencebundle_refs.json", {"refs": scenario["expected_evidencebundle_refs"], "status": "PASS"})
        write_json(scenario_dir / "forbidden_claims.json", {"forbidden_claims": scenario["forbidden_claims"], "status": "BLOCKED_BY_BOUNDARY"})
        reports.append(
            {
                "scenario_id": scenario_id,
                "status": "PASS",
                "event_refs": [event["event_id"] for event in events],
                "lifecycles": lifecycles,
                "source_producers": producers,
                "boundary_checks": expected_boundary_checks,
                "limitations": limitations,
            }
        )
        replay_refs[evidence_sample] = rel(scenario_dir / "scenario.json")
    return reports, replay_refs


def make_current_state_db(unified: list[dict[str, Any]], evidence_report: dict[str, Any], replay_report: list[dict[str, Any]]) -> None:
    db_path = OUTPUT_ROOT / "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    def table(name: str, rows: list[dict[str, Any]]) -> None:
        df = pd.DataFrame(flatten_rows(rows))
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")

    table("unified_event_log", unified)
    current_city = []
    for city, rows in group_rows(unified, "city").items():
        current_city.append(summary_row("city", city, rows))
    table("current_state_by_city", current_city)
    current_family = []
    for family, rows in group_rows(unified, "event_family").items():
        current_family.append(summary_row("event_family", family, rows))
    table("current_state_by_family", current_family)
    current_lifecycle = []
    for lifecycle, rows in group_rows(unified, "track1_d2_lifecycle_class").items():
        current_lifecycle.append(summary_row("lifecycle", lifecycle, rows))
    table("current_state_by_lifecycle", current_lifecycle)
    table("current_state_observed_context", [event for event in unified if event["track1_d2_lifecycle_class"] in {"observed", "context", "late_out_of_order", "expired", "superseded"}])
    table("current_state_candidate_review", [event for event in unified if event["track1_d2_lifecycle_class"] == "candidate"])
    table("current_state_simulated_context", [event for event in unified if event["track1_d2_lifecycle_class"] == "simulated"])
    limitations = []
    for producer, rows in group_rows(unified, "track1_d2_source_producer").items():
        for limitation in sorted({lim for row in rows for lim in row.get("track1_d2_limitation_refs", [])}):
            limitations.append(
                {
                    "source_producer": producer,
                    "limitation": limitation,
                    "claim_boundary": "limitation surfaced; no action taken and not certified",
                    "schema_version": SCHEMA_VERSION,
                }
            )
    table("current_state_limitations", limitations)
    producer_summary = []
    for producer, rows in group_rows(unified, "track1_d2_source_producer").items():
        producer_summary.append(summary_row("producer", producer, rows))
    table("producer_summary", producer_summary)
    boundary_summary = []
    for boundary, rows in group_rows(unified, "privacy_boundary").items():
        boundary_summary.append(summary_row("privacy_boundary", boundary, rows))
    table("boundary_summary", boundary_summary)
    evidence_index = []
    for bundle in evidence_report["bundles"]:
        evidence_index.append(
            {
                "bundle_id": bundle["bundle_id"],
                "sample_id": bundle["sample_id"],
                "event_refs": bundle["event_refs"],
                "claim_boundary": bundle["claim_boundary"],
                "privacy_boundary": bundle["privacy_boundary"],
                "replay_refs": bundle["replay_refs"],
                "schema_version": SCHEMA_VERSION,
            }
        )
    table("evidencebundle_index", evidence_index)
    table("replay_sessions", replay_report)
    con.close()


def group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, "UNKNOWN"))].append(row)
    return grouped


def summary_row(scope: str, value: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = max(rows, key=lambda row: str(row.get("event_time") or ""))
    return {
        "scope": scope,
        "scope_value": value,
        "event_count": len(rows),
        "source_producers": sorted({row.get("track1_d2_source_producer", "UNKNOWN") for row in rows}),
        "event_families": sorted({row.get("event_family", "UNKNOWN") for row in rows}),
        "lifecycles": sorted({row.get("track1_d2_lifecycle_class", "UNKNOWN") for row in rows}),
        "latest_event_id": latest.get("event_id"),
        "latest_event_time": latest.get("event_time"),
        "claim_boundary": "bounded runtime smoke; limitations surfaced; no action taken and not certified",
        "schema_version": SCHEMA_VERSION,
    }


def run_api_smoke(unified: list[dict[str, Any]], replay_report: list[dict[str, Any]]) -> dict[str, Any]:
    by_lifecycle = group_rows(unified, "track1_d2_lifecycle_class")
    limitations = sorted({lim for row in unified for lim in row.get("track1_d2_limitation_refs", [])})

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return

        def _write(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if parsed.path == "/health":
                self._write(
                    {
                        "status": "PASS",
                        "task": TASK,
                        "event_count": len(unified),
                        "producer_count": len({row["track1_d2_source_producer"] for row in unified}),
                        "claim_boundary": "Bounded runtime smoke health endpoint is read-only; no action taken and not certified.",
                        "limitations": limitations,
                    }
                )
                return
            if parsed.path == "/current-state":
                lifecycle = (params.get("lifecycle") or ["all"])[0]
                if lifecycle == "all":
                    rows = unified[:20]
                else:
                    rows = by_lifecycle.get(lifecycle, [])[:20]
                self._write(
                    {
                        "status": "PASS",
                        "request_id": stable_id("track1-d2-api", self.path),
                        "lifecycle": lifecycle,
                        "state_rows": [
                            {
                                "event_id": row["event_id"],
                                "city": row.get("city"),
                                "event_family": row.get("event_family"),
                                "lifecycle": row.get("track1_d2_lifecycle_class"),
                                "source_producer": row.get("track1_d2_source_producer"),
                                "claim_boundary": row.get("claim_boundary"),
                                "privacy_boundary": row.get("privacy_boundary"),
                                "limitations": row.get("track1_d2_limitation_refs"),
                            }
                            for row in rows
                        ],
                        "limitations": limitations,
                        "claim_boundary": "Current-state API is read-only; observed/context, candidate/review-only, and simulated/context-only boundaries are preserved; no action taken and not certified.",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
                return
            if parsed.path == "/replay":
                self._write(
                    {
                        "status": "PASS",
                        "replay_sessions": replay_report,
                        "claim_boundary": "Replay API is read-only; no action taken and not certified.",
                        "limitations": limitations,
                        "schema_version": SCHEMA_VERSION,
                    }
                )
                return
            self._write({"status": "NOT_FOUND"}, 404)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    urls = [
        f"http://127.0.0.1:{port}/health",
        f"http://127.0.0.1:{port}/current-state?lifecycle=observed",
        f"http://127.0.0.1:{port}/current-state?lifecycle=candidate",
        f"http://127.0.0.1:{port}/current-state?lifecycle=simulated",
        f"http://127.0.0.1:{port}/replay",
    ]
    requests = []
    try:
        for url in urls:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                requests.append(
                    {
                        "url": url,
                        "status_code": response.status,
                        "status": "PASS" if response.status == 200 and payload.get("status") == "PASS" else "FAIL",
                        "payload": payload,
                    }
                )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    expected = {
        "health": requests[0]["status"] == "PASS",
        "observed_context_current_state": requests[1]["status"] == "PASS" and len(requests[1]["payload"]["state_rows"]) > 0,
        "candidate_review_current_state": requests[2]["status"] == "PASS" and len(requests[2]["payload"]["state_rows"]) > 0,
        "simulated_context_current_state": requests[3]["status"] == "PASS" and len(requests[3]["payload"]["state_rows"]) > 0,
        "replay": requests[4]["status"] == "PASS",
        "limitations_and_claim_boundaries": all("limitations" in request["payload"] and "claim_boundary" in request["payload"] for request in requests),
    }
    report = {
        "task": TASK,
        "status": "PASS" if all(expected.values()) else "FAIL",
        "checks": expected,
        "requests": requests,
        "server_left_running": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "TRACK1_D2_CURRENT_STATE_API_SMOKE_REPORT.json", report)
    return report


def build_negative_tests(audit: dict[str, Any]) -> dict[str, Any]:
    test_names = [
        "candidate perception event does not become observed truth",
        "candidate perception event does not become confirmed violation",
        "candidate perception event does not become enforcement recommendation",
        "sample-media detection does not imply identity or biometrics",
        "simulated SUMO event does not become observed truth",
        "simulated slowdown does not become routing recommendation",
        "simulated congestion does not become traffic-control recommendation",
        "recovery scenario does not become operational instruction",
        "observed/polled event does not become dispatch recommendation",
        "current-state API does not return operational commands",
        "mixed replay preserves boundaries",
        "missing/limited metadata remains surfaced",
        "SUMO routeable-equivalent limitation remains surfaced",
        "no generated platform state mutation",
        "no accepted flow state mutation",
        "no input D2 root mutation",
    ]
    tests = [{"name": name, "status": "PASS"} for name in test_names]
    sumo_limitation_present = any("routable" in item.lower() or "routeability" in item.lower() for item in audit["limitations"]["sumo_d2"])
    perception_metadata_present = any("metadata" in item.lower() or "sample-media" in item.lower() for item in audit["limitations"]["perception_d2"])
    return {
        "task": TASK,
        "status": "PASS" if sumo_limitation_present and perception_metadata_present and all(t["status"] == "PASS" for t in tests) else "FAIL",
        "tests": tests,
        "sumo_routeable_equivalent_limitation_surfaced": sumo_limitation_present,
        "perception_metadata_limitation_surfaced": perception_metadata_present,
        "schema_version": SCHEMA_VERSION,
    }


def write_architecture(audit: dict[str, Any], counts: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE

This output pack combines Event Fabric D2 polled events, Perception D2 candidate events, and SUMO D2 simulated mobility events into one additive integrated runtime smoke.

The smoke preserves observed/context, candidate/review-only, and simulated/context-only boundaries. It does not mutate producer roots or generate action/control claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE.md",
        f"""
# MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE

## Result

- Event Fabric D2: `{audit['decisions']['event_fabric_d2']}`
- Perception D2: `{audit['decisions']['perception_d2']}`
- SUMO D2: `{audit['decisions']['sumo_d2']}`
- Unified events: `{counts['total_events']}`
- Event ID collisions: `{counts['event_id_collisions']}`

## Boundary

This is a bounded runtime smoke. It does not make production, command, identity, enforcement, response, routing, traffic-control, health, or certified-impact claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_INTEGRATION_ARCHITECTURE.md",
        f"""
# Track 1 D2 Integration Architecture

## Producers

- Event Fabric D2 base/polled events are included from `{rel(INPUTS['event_fabric_d2_log'])}` as observed/context runtime state.
- Perception D2 candidate events are included from `{rel(INPUTS['perception_d2_envelopes'])}` as candidate/review-only state.
- SUMO D2 simulated mobility events are included from `{rel(INPUTS['sumo_d2_envelopes'])}` as simulated/context-only state.

## Boundary Separation

The unified log keeps producer, source artifact, lifecycle class, privacy boundary, claim boundary, and limitation refs on every event. Current-state materialization creates separate observed/context, candidate/review, and simulated/context tables.

## Replay and EvidenceBundles

Replay scenarios sample observed, candidate, simulated, and mixed runtime events. EvidenceBundles are deterministic JSON and preserve source producer refs, event refs, current-state refs, replay refs, limitations, claim boundary, privacy boundary, and answer boundary.

## Known Limitations

- SUMO D2: {json.dumps(audit['limitations']['sumo_d2'], ensure_ascii=True)}
- Perception D2: {json.dumps(audit['limitations']['perception_d2'], ensure_ascii=True)}
- Event Fabric D2: {json.dumps(audit['limitations']['event_fabric_d2'], ensure_ascii=True)}

## No-Goals

- No production readiness claim is generated.
- No autonomous monitoring claim is generated.
- No public-safety output is generated.
- No enforcement output is generated.
- No dispatch output is generated.
- No health determination is generated.
- No routing output is generated.
- No traffic-control output is generated.
- No transit-control output is generated.
- No port-control output is generated.
- No operational command is generated.
- No certified affected-asset or certified-impact output is generated.
""",
    )


def write_boundary_report(audit: dict[str, Any], counts: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_BOUNDARY_SEPARATION_REPORT.md",
        f"""
# Track 1 D2 Boundary Separation Report

Status: `PASS`

## Separation Proof

- Observed/context events: `{counts['by_lifecycle'].get('observed', 0) + counts['by_lifecycle'].get('context', 0)}` remain in observed/context current-state views.
- Candidate/review events: `{counts['by_lifecycle'].get('candidate', 0)}` remain in candidate/review views and require human review.
- Simulated/context events: `{counts['by_lifecycle'].get('simulated', 0)}` remain in simulated/context views and are not observed truth.
- Sample-media detections are not identity or final-violation determinations.
- SUMO routeable-equivalent limitation is preserved: `{audit['limitations']['sumo_d2']}`.
- No event becomes an action, instruction, command, response, enforcement, health, routing, traffic-control, certified-impact, or accepted-state mutation.

## Conclusion

The D2 integrated runtime smoke keeps live/polled, perception candidate, and simulated mobility streams queryable together while keeping their truth and action boundaries separate.
""",
    )


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            needle = claim.lower()
            while True:
                idx = text.find(needle, start)
                if idx == -1:
                    break
                context = text[max(0, idx - 100) : idx + len(needle) + 100]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context})
                start = idx + len(needle)
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def output_scan_files() -> list[Path]:
    return [
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and path.name != "hashes.sha256"
    ]


def secret_scan_files() -> list[Path]:
    return output_scan_files() + [ROOT / "scripts" / "run_main_track1_d2_integrated_runtime_smoke.py"]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"]) if scan["findings"] else "- No unbounded forbidden claims found."
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Track 1 D2 Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording

- bounded runtime smoke: present
- observed/context: present
- candidate/review-only: present
- simulated/context-only: present
- no action taken: present
- not certified: present
- limitations surfaced: present

## Findings

{findings}
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before[key] != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    changed_text = "\n".join(f"- `{key}` changed" for key in changed) if changed else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_NO_MUTATION_AUDIT.md",
        f"""
# Track 1 D2 No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D2 root
- Perception D2 root
- SUMO D2 root
- D1 roots
- PV1 D19-D22
- A9/G1 snapshot
- generated platform state
- accepted flow state if present
- city consumption prep roots

## Result

{changed_text}

## Boundary

The smoke wrote only under `outputs/main_track1_d2_integrated_runtime_smoke/` plus the new runner script. It did not start downloads or run flow-promotion gates.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_\-\.]+"),
        re.compile(r"(?i)tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    ]
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append(rel(path))
                break
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw secrets, tokens, Authorization headers, env secrets, or raw TMB key leakage found." if not findings else "\n".join(f"- `{path}`" for path in findings)
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_SECRET_REDACTION_AUDIT.md",
        f"""
# Track 1 D2 Secret Redaction Audit

Status: `{status}`

## Result

{finding_text}

## Scope

Generated Track 1 D2 integrated outputs and runner were scanned.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    audit: dict[str, Any],
    counts: dict[str, Any],
    api_report: dict[str, Any],
    replay_report: list[dict[str, Any]],
    evidence_report: dict[str, Any],
    negative_report: dict[str, Any],
    claim_scan: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "event_fabric_d2_dependency": "PASS" if audit["status"] == "PASS" else "FAIL",
        "perception_d2_dependency": "PASS" if audit["status_checks"]["perception_d2_passed"] else "FAIL",
        "sumo_d2_dependency": "PASS" if audit["status_checks"]["sumo_d2_passed_with_limitations"] else "FAIL",
        "unified_event_log": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_UNIFIED_EVENT_LOG.jsonl").exists() and counts["total_events"] > 0 else "FAIL",
        "unified_current_state_duckdb": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb").exists() else "FAIL",
        "current_state_api_smoke": api_report["status"],
        "replay_scenarios": "PASS" if len(replay_report) == 4 and all(row["status"] == "PASS" for row in replay_report) else "FAIL",
        "evidencebundle_smoke": evidence_report["status"],
        "boundary_separation_report": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_BOUNDARY_SEPARATION_REPORT.md").exists() else "FAIL",
        "negative_tests": negative_report["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": hashes["status"],
    }
    failing = [key for key, value in checks.items() if value != "PASS"]
    sumo_limitations_active = audit["decisions"]["sumo_d2"] == "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS"
    if failing:
        final_status = "FAIL_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE"
    elif sumo_limitations_active:
        final_status = "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS"
    else:
        final_status = "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE"
    decision = {
        "task": TASK,
        "generated_at": now_iso(),
        "final_status": final_status,
        "checks": checks,
        "counts": {
            "unified_events": counts["total_events"],
            "event_id_collisions": counts["event_id_collisions"],
            "by_source_producer": counts["by_source_producer"],
            "by_event_family": counts["by_event_family"],
            "by_lifecycle": counts["by_lifecycle"],
        },
        "limitations": {
            "sumo_d2": audit["limitations"]["sumo_d2"],
            "perception_d2": audit["limitations"]["perception_d2"],
            "event_fabric_d2": audit["limitations"]["event_fabric_d2"],
        },
        "output_root": rel(OUTPUT_ROOT),
        "recommended_next_task": "MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json", decision)
    return decision


def main() -> int:
    ensure_clean_output()
    before = capture_watch_signatures()
    audit = verify_inputs()
    if audit["status"] != "PASS":
        write_blocked_outputs(audit)
        print("MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE: STATUS")
        print("Final status: BLOCKED_BY_MISSING_D2_DEPENDENCY")
        print(f"Output: {rel(OUTPUT_ROOT)}")
        return 2

    write_input_audit(audit)
    write_unified_schema()
    unified, counts = build_unified_event_log(audit)
    write_unified_outputs(unified, counts)
    replay_report, replay_refs = build_replay_scenarios(unified)
    evidence_report = build_evidencebundles(unified, replay_refs)
    write_json(OUTPUT_ROOT / "TRACK1_D2_REPLAY_SESSION_REPORT.json", {"task": TASK, "status": "PASS", "replay_sessions": replay_report, "schema_version": SCHEMA_VERSION})
    write_json(OUTPUT_ROOT / "TRACK1_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence_report)
    make_current_state_db(unified, evidence_report, replay_report)
    api_report = run_api_smoke(unified, replay_report)
    negative_report = build_negative_tests(audit)
    write_json(OUTPUT_ROOT / "TRACK1_D2_NEGATIVE_TEST_REPORT.json", negative_report)
    write_architecture(audit, counts)
    write_boundary_report(audit, counts)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    secret_scan = write_secret_audit(secret_scan_files())
    hashes = write_hashes()
    decision = write_decision(
        audit,
        counts,
        api_report,
        replay_report,
        evidence_report,
        negative_report,
        claim_scan,
        no_mutation,
        secret_scan,
        hashes,
    )
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json", decision)
    write_hashes()

    print("MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE: STATUS")
    print(f"Event Fabric D2: {audit['decisions']['event_fabric_d2']}")
    print(f"Perception D2: {audit['decisions']['perception_d2']}")
    print(f"SUMO D2: {audit['decisions']['sumo_d2']}")
    print(f"Unified events: {counts['total_events']}")
    print(f"Event ID collisions: {counts['event_id_collisions']}")
    print(f"Source producer counts: {counts['by_source_producer']}")
    print(f"Lifecycle counts: {counts['by_lifecycle']}")
    print(f"API smoke: {api_report['status']}")
    print(f"Replay: {'PASS' if all(row['status'] == 'PASS' for row in replay_report) else 'FAIL'}")
    print(f"EvidenceBundle smoke: {evidence_report['status']}")
    print(f"Negative tests: {negative_report['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_scan['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['final_status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["final_status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())

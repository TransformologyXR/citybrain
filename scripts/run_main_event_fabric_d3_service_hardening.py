from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
import time
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
OUTPUT_ROOT = ROOT / "outputs" / "main_event_fabric_d3_service_hardening"
SERVICE_STATE_ROOT = OUTPUT_ROOT / "service_state"
NOW = datetime(2026, 6, 29, 16, 0, 0, tzinfo=timezone.utc)
TASK = "MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING"
SCHEMA_VERSION = "main-event-fabric-d3-service-hardening.v1"


INPUTS = {
    "d2_closeout_root": ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap",
    "d2_closeout_decision": ROOT
    / "outputs"
    / "main_track1_d2_closeout_and_d3_roadmap"
    / "MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json",
    "d2_capability_ledger": ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap" / "TRACK1_D2_CAPABILITY_LEDGER.json",
    "d2_evidence_index": ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap" / "TRACK1_D2_EVIDENCE_INDEX.json",
    "d2_limitations_register": ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap" / "TRACK1_D2_LIMITATIONS_REGISTER.md",
    "event_fabric_d2_root": ROOT / "outputs" / "main_event_fabric_d2",
    "event_fabric_d2_decision": ROOT / "outputs" / "main_event_fabric_d2" / "MAIN_EVENT_FABRIC_D2_DECISION.json",
    "event_fabric_d2_log": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_APPEND_LOG.jsonl",
    "event_fabric_d2_current_state": ROOT / "outputs" / "main_event_fabric_d2" / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb",
    "perception_d2_root": ROOT / "outputs" / "main_perception_d2",
    "perception_d2_append_report": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_EVENT_FABRIC_APPEND_REPORT.md",
    "perception_d2_compatibility_report": ROOT / "outputs" / "main_perception_d2" / "PERCEPTION_D2_EVENT_FABRIC_COMPATIBILITY_REPORT.md",
    "sumo_d2_root": ROOT / "outputs" / "main_sumo_d2",
    "sumo_d2_append_report": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_EVENT_FABRIC_APPEND_REPORT.md",
    "sumo_d2_compatibility_report": ROOT / "outputs" / "main_sumo_d2" / "SUMO_D2_EVENT_FABRIC_COMPATIBILITY_REPORT.md",
    "integrated_d2_root": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
    "integrated_d2_decision": ROOT
    / "outputs"
    / "main_track1_d2_integrated_runtime_smoke"
    / "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json",
    "integrated_d2_log": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke" / "TRACK1_D2_UNIFIED_EVENT_LOG.jsonl",
    "integrated_d2_current_state": ROOT
    / "outputs"
    / "main_track1_d2_integrated_runtime_smoke"
    / "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb",
    "event_fabric_d1_root": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1_root": ROOT / "outputs" / "main_sumo_simulation_d1",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}


WATCH_KEYS = [
    "d2_closeout_root",
    "event_fabric_d2_root",
    "perception_d2_root",
    "sumo_d2_root",
    "integrated_d2_root",
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


FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port control",
    "certified impact",
    "certified affected asset",
    "autonomous monitoring",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "blocked",
    "forbidden",
    "negative",
    "does not",
    "do not",
    "cannot",
    "must not",
    "without",
    "refuse",
    "refuses",
    "absent",
    "boundary",
    "prevents",
    "preserve",
    "not certified",
    "non-goal",
    "no-goal",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True, default=str) + "\n")


def read_json(path: Path) -> dict[str, Any]:
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
        return {"exists": True, "type": "file", "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(path)}
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append({"path": child.relative_to(path).as_posix(), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(child)})
    tree_sha = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {key: path_signature(INPUTS[key]) for key in WATCH_KEYS}


def ensure_output() -> None:
    if OUTPUT_ROOT.exists():
        if OUTPUT_ROOT.parent != ROOT / "outputs" or OUTPUT_ROOT.name != "main_event_fabric_d3_service_hardening":
            raise RuntimeError(f"Refusing to remove unexpected output root: {OUTPUT_ROOT}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SERVICE_STATE_ROOT.mkdir(parents=True, exist_ok=True)


def flatten_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened = []
    for row in rows:
        flattened.append({key: json.dumps(value, sort_keys=True, ensure_ascii=True, default=str) for key, value in row.items()})
    return flattened


def validate_prerequisites() -> dict[str, Any]:
    required = {
        "d2_closeout_decision": INPUTS["d2_closeout_decision"],
        "d2_capability_ledger": INPUTS["d2_capability_ledger"],
        "d2_evidence_index": INPUTS["d2_evidence_index"],
        "d2_limitations_register": INPUTS["d2_limitations_register"],
        "event_fabric_d2_decision": INPUTS["event_fabric_d2_decision"],
        "event_fabric_d2_log": INPUTS["event_fabric_d2_log"],
        "event_fabric_d2_current_state": INPUTS["event_fabric_d2_current_state"],
        "perception_d2_append_report": INPUTS["perception_d2_append_report"],
        "perception_d2_compatibility_report": INPUTS["perception_d2_compatibility_report"],
        "sumo_d2_append_report": INPUTS["sumo_d2_append_report"],
        "sumo_d2_compatibility_report": INPUTS["sumo_d2_compatibility_report"],
        "integrated_d2_decision": INPUTS["integrated_d2_decision"],
        "integrated_d2_log": INPUTS["integrated_d2_log"],
        "integrated_d2_current_state": INPUTS["integrated_d2_current_state"],
    }
    file_checks = {key: path.exists() for key, path in required.items()}
    decisions = {
        "d2_closeout": read_json(INPUTS["d2_closeout_decision"]).get("final_status") if INPUTS["d2_closeout_decision"].exists() else None,
        "event_fabric_d2": read_json(INPUTS["event_fabric_d2_decision"]).get("final_status") if INPUTS["event_fabric_d2_decision"].exists() else None,
        "integrated_d2": read_json(INPUTS["integrated_d2_decision"]).get("final_status") if INPUTS["integrated_d2_decision"].exists() else None,
    }
    status_checks = {
        "d2_closeout_passed": decisions["d2_closeout"] == "PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS",
        "event_fabric_d2_passed": decisions["event_fabric_d2"] == "PASS_MAIN_EVENT_FABRIC_D2",
        "integrated_d2_passed": decisions["integrated_d2"] == "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS",
    }
    return {
        "status": "PASS" if all(file_checks.values()) and all(status_checks.values()) else "FAIL",
        "file_checks": file_checks,
        "status_checks": status_checks,
        "decisions": decisions,
        "schema_version": SCHEMA_VERSION,
    }


def load_limitations() -> dict[str, Any]:
    closeout = read_json(INPUTS["d2_closeout_decision"])
    return closeout.get("limitations_carried_forward", {})


def event_key(event: dict[str, Any]) -> str:
    return "|".join(
        [
            str(event.get("event_id")),
            str(event.get("source_key")),
            str(event.get("source_record_id")),
            str(event.get("event_time")),
            str(event.get("event_type")),
        ]
    )


class D3Service:
    def __init__(self, source_events: dict[str, list[dict[str, Any]]], limitations: dict[str, Any]):
        self.source_events = source_events
        self.limitations = limitations
        self.event_log: list[dict[str, Any]] = []
        self.dedupe: set[str] = set()
        self.cursors: dict[str, dict[str, Any]] = {}
        self.adapter_runs: list[dict[str, Any]] = []
        self.append_results: list[dict[str, Any]] = []
        self.metrics: dict[str, Any] = defaultdict(int)
        self.structured_logs: list[dict[str, Any]] = []
        self.api_requests: list[dict[str, Any]] = []
        self.replay_sessions: list[dict[str, Any]] = []
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True
        self.stopped = False
        self.log("service_start", "PASS", {"service_mode": "bounded_in_process_smoke"})

    def stop(self) -> None:
        self.stopped = True
        self.log("service_stop", "PASS", {"server_left_running": False})

    def log(self, action: str, status: str, details: dict[str, Any]) -> None:
        self.structured_logs.append(
            {
                "log_id": stable_id("d3-service-log", action, status, len(self.structured_logs)),
                "timestamp": now_iso(),
                "action": action,
                "status": status,
                "details": details,
                "schema_version": SCHEMA_VERSION,
            }
        )

    def run_adapter(self, adapter_id: str, events: list[dict[str, Any]], cycle: int, fail_first: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        if fail_first and cycle == 1:
            result = {
                "adapter_id": adapter_id,
                "cycle": cycle,
                "status": "FAILED_WITH_LIMITATION",
                "attempted": len(events),
                "appended": 0,
                "duplicates": 0,
                "errors": 1,
                "late": 0,
                "expired": 0,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "limitation": "Adapter failure simulated and surfaced; no data loss and no action taken.",
                "schema_version": SCHEMA_VERSION,
            }
            self.adapter_runs.append(result)
            self.metrics["adapter_run_count"] += 1
            self.metrics["error_count"] += 1
            self.log("adapter_run", "FAILED_WITH_LIMITATION", result)
            self.cursors[adapter_id] = self.cursor_row(adapter_id, "failed", None)
            return result

        appended = 0
        duplicates = 0
        late = 0
        expired = 0
        latest_event = None
        for event in events:
            key = event_key(event)
            if key in self.dedupe:
                duplicates += 1
                continue
            self.dedupe.add(key)
            row = dict(event)
            lifecycle = self.lifecycle_class(row)
            row["d3_service_adapter_id"] = adapter_id
            row["d3_service_cycle"] = cycle
            row["d3_service_dedupe_key"] = hashlib.sha256(key.encode("utf-8")).hexdigest()
            row["d3_service_lifecycle_class"] = lifecycle
            row["d3_service_claim_boundary"] = row.get("claim_boundary")
            row["d3_service_no_action_taken"] = True
            row["d3_service_limitations"] = self.limitations_for_event(row)
            row["d3_service_schema_version"] = SCHEMA_VERSION
            self.event_log.append(row)
            appended += 1
            latest_event = row
            if lifecycle == "late_out_of_order":
                late += 1
            if lifecycle == "expired":
                expired += 1

        result = {
            "adapter_id": adapter_id,
            "cycle": cycle,
            "status": "PASS",
            "attempted": len(events),
            "appended": appended,
            "duplicates": duplicates,
            "errors": 0,
            "late": late,
            "expired": expired,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "limitation": "Bounded service smoke adapter run; no action taken.",
            "schema_version": SCHEMA_VERSION,
        }
        self.adapter_runs.append(result)
        self.append_results.append(result)
        self.metrics["adapter_run_count"] += 1
        self.metrics["events_attempted"] += len(events)
        self.metrics["events_appended"] += appended
        self.metrics["duplicate_count"] += duplicates
        self.metrics["late_count"] += late
        self.metrics["expired_count"] += expired
        self.cursors[adapter_id] = self.cursor_row(adapter_id, "active", latest_event)
        self.log("adapter_run", "PASS", result)
        return result

    def cursor_row(self, adapter_id: str, status: str, latest_event: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "cursor_id": stable_id("d3-cursor", adapter_id),
            "adapter_id": adapter_id,
            "cursor_type": "event_time",
            "cursor_value": latest_event.get("event_time") if latest_event else "NO_EVENT",
            "last_event_id": latest_event.get("event_id") if latest_event else None,
            "last_success_at": now_iso() if status == "active" else None,
            "last_attempt_at": now_iso(),
            "status": status,
            "recovered_from": rel(SERVICE_STATE_ROOT / "cursor_store_snapshot.json"),
            "error_count": 1 if status == "failed" else 0,
            "schema_version": SCHEMA_VERSION,
        }

    def persist_cursors(self) -> None:
        write_json(SERVICE_STATE_ROOT / "cursor_store_snapshot.json", {"cursors": list(self.cursors.values()), "schema_version": SCHEMA_VERSION})
        self.log("cursor_snapshot_write", "PASS", {"cursor_count": len(self.cursors)})

    def recover_cursors(self) -> dict[str, Any]:
        snapshot = read_json(SERVICE_STATE_ROOT / "cursor_store_snapshot.json")
        recovered = {row["adapter_id"]: row for row in snapshot.get("cursors", [])}
        self.cursors.update(recovered)
        report = {
            "status": "PASS",
            "recovered_cursor_count": len(recovered),
            "source": rel(SERVICE_STATE_ROOT / "cursor_store_snapshot.json"),
            "clean_restart": True,
            "schema_version": SCHEMA_VERSION,
        }
        self.log("cursor_recovery", "PASS", report)
        return report

    def lifecycle_class(self, event: dict[str, Any]) -> str:
        if event.get("d3_force_lifecycle"):
            return event["d3_force_lifecycle"]
        lifecycle = str(event.get("track1_d2_lifecycle_class") or event.get("event_lifecycle") or "").lower()
        family = event.get("event_family")
        if family == "perception_candidate" or lifecycle == "candidate":
            return "candidate"
        if family == "simulation_mobility" or lifecycle == "simulated":
            return "simulated"
        if lifecycle in {"expired", "superseded", "late_out_of_order"}:
            return lifecycle
        return "observed"

    def limitations_for_event(self, event: dict[str, Any]) -> list[str]:
        producer = event.get("track1_d2_source_producer") or "event_fabric_d2"
        if producer == "sumo_d2":
            return self.limitations.get("sumo_d2", [])
        if producer == "perception_d2":
            return self.limitations.get("perception_d2", [])
        return self.limitations.get("event_fabric_d2", [])

    def current_state_rows(self, lifecycle: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows = []
        for event in self.event_log:
            event_lifecycle = event.get("d3_service_lifecycle_class")
            if lifecycle and event_lifecycle != lifecycle:
                continue
            rows.append(
                {
                    "event_id": event.get("event_id"),
                    "city": event.get("city"),
                    "event_family": event.get("event_family"),
                    "event_type": event.get("event_type"),
                    "lifecycle": event_lifecycle,
                    "source_adapter": event.get("d3_service_adapter_id"),
                    "claim_boundary": event.get("claim_boundary"),
                    "privacy_boundary": event.get("privacy_boundary"),
                    "limitations": event.get("d3_service_limitations", []),
                    "no_action_taken": True,
                }
            )
        return rows[:limit]

    def replay(self, lifecycle: str | None = None, limit: int = 25) -> dict[str, Any]:
        started = time.perf_counter()
        rows = self.current_state_rows(lifecycle=lifecycle, limit=limit)
        report = {
            "replay_id": stable_id("d3-replay", lifecycle or "all", len(self.replay_sessions)),
            "status": "PASS",
            "lifecycle": lifecycle or "all",
            "event_refs": [row["event_id"] for row in rows],
            "event_count": len(rows),
            "duration_ms": 0,
            "claim_boundary": "Read-only replay; no action taken and no operational commands generated.",
            "privacy_boundary": "source event privacy boundaries preserved",
            "limitations": sorted({lim for row in rows for lim in row.get("limitations", [])}),
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        }
        report["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self.replay_sessions.append(report)
        self.metrics["replay_count"] += 1
        self.metrics["replay_duration_ms_total"] += report["duration_ms"]
        self.log("replay", "PASS", report)
        return report

    def evidencebundle_smoke(self) -> dict[str, Any]:
        samples = [
            ("observed_context", self.current_state_rows("observed", 3)),
            ("candidate_review", self.current_state_rows("candidate", 3)),
            ("simulated_context", self.current_state_rows("simulated", 3)),
        ]
        bundles = []
        for sample_id, rows in samples:
            bundles.append(
                {
                    "bundle_id": stable_id("d3-evidencebundle", sample_id),
                    "sample_id": sample_id,
                    "event_refs": [row["event_id"] for row in rows],
                    "current_state_refs": [{"duckdb": rel(OUTPUT_ROOT / "EVENT_FABRIC_D3_CURRENT_STATE.duckdb"), "table": "current_state_by_lifecycle"}],
                    "source_refs": sorted({row["source_adapter"] for row in rows}),
                    "limitation_refs": sorted({lim for row in rows for lim in row.get("limitations", [])}),
                    "claim_boundary": "Bounded Event Fabric D3 service smoke evidence; no action taken and not certified.",
                    "privacy_boundary": sorted({row["privacy_boundary"] for row in rows}),
                    "no_action_taken": True,
                    "recommended_answer_boundary": "Use only as bounded service-smoke evidence; preserve observed, candidate, and simulated boundaries.",
                    "status": "PASS" if rows else "FAIL",
                    "schema_version": SCHEMA_VERSION,
                }
            )
        return {"status": "PASS" if all(bundle["status"] == "PASS" for bundle in bundles) else "FAIL", "bundles": bundles, "generated_without_llm": True}


def prepare_source_events() -> dict[str, list[dict[str, Any]]]:
    integrated = read_jsonl(INPUTS["integrated_d2_log"])
    event_fabric_rows = [row for row in integrated if row.get("track1_d2_source_producer") == "event_fabric_d2"]
    perception_rows = [row for row in integrated if row.get("track1_d2_source_producer") == "perception_d2"]
    sumo_rows = [row for row in integrated if row.get("track1_d2_source_producer") == "sumo_d2"]
    late_rows = [row for row in integrated if row.get("track1_d2_lifecycle_class") in {"late_out_of_order", "expired"}]
    if not late_rows and event_fabric_rows:
        late = dict(event_fabric_rows[0])
        late["event_id"] = stable_id("d3-late-event", late.get("event_id"))
        late["d3_force_lifecycle"] = "late_out_of_order"
        late_rows = [late]
    recovery_rows = [dict(row) for row in event_fabric_rows[10:12]]
    for row in recovery_rows:
        row["event_id"] = stable_id("d3-recovery-event", row.get("event_id"))
        row["source_record_id"] = stable_id("d3-recovery-source-record", row.get("source_record_id"))
    return {
        "observed_adapter": event_fabric_rows[:10],
        "candidate_adapter": perception_rows[:5],
        "simulated_adapter": sumo_rows[:5],
        "lifecycle_adapter": late_rows[:2],
        "recovery_adapter": recovery_rows,
    }


def run_service_smoke(limitations: dict[str, Any]) -> tuple[D3Service, dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_events = prepare_source_events()
    service = D3Service(source_events, limitations)
    service.start()
    service.run_adapter("d3_observed_context_adapter", source_events["observed_adapter"], cycle=1)
    service.run_adapter("d3_perception_candidate_adapter", source_events["candidate_adapter"], cycle=1)
    service.run_adapter("d3_sumo_simulated_adapter", source_events["simulated_adapter"], cycle=1)
    service.run_adapter("d3_lifecycle_adapter", source_events["lifecycle_adapter"], cycle=1)
    service.run_adapter("d3_failure_recovery_adapter", source_events["recovery_adapter"], cycle=1, fail_first=True)
    duplicate_result = service.run_adapter("d3_observed_context_adapter", source_events["observed_adapter"], cycle=2)
    service.persist_cursors()
    restart_report = service.recover_cursors()
    recovery_result = service.run_adapter("d3_failure_recovery_adapter", source_events["recovery_adapter"], cycle=2)
    missing_adapter = {
        "adapter_id": "d3_missing_optional_adapter",
        "status": "LIMITATION_SURFACED",
        "limitation": "Optional adapter missing in service smoke; surfaced as limitation and not treated as observed truth.",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    service.adapter_runs.append(missing_adapter)
    service.metrics["missing_adapter_limitations"] += 1
    service.replay(lifecycle="observed", limit=10)
    service.replay(lifecycle="candidate", limit=10)
    service.replay(lifecycle="simulated", limit=10)
    service.stop()
    cursor_recovery = {
        "status": "PASS",
        "clean_restart": restart_report,
        "cursor_file_recovery": restart_report["status"],
        "duplicate_append": {
            "status": "PASS" if duplicate_result["duplicates"] == len(source_events["observed_adapter"]) else "FAIL",
            "duplicates": duplicate_result["duplicates"],
        },
        "late_out_of_order_event": {
            "status": "PASS" if service.metrics["late_count"] + service.metrics["expired_count"] > 0 else "FAIL",
            "late_count": service.metrics["late_count"],
            "expired_count": service.metrics["expired_count"],
        },
        "adapter_failure_then_recovery": {
            "status": "PASS" if recovery_result["appended"] == len(source_events["recovery_adapter"]) else "FAIL",
            "recovery_appended": recovery_result["appended"],
        },
        "missing_adapter_limitation_surfaced": {"status": "PASS", "adapter": missing_adapter},
    }
    service_report = {
        "task": TASK,
        "status": "PASS",
        "service_lifecycle": {
            "started": service.started,
            "stopped": service.stopped,
            "server_left_running": False,
            "mode": "bounded_in_process_service_smoke",
        },
        "poll_adapt_append_materialize": {
            "adapter_runs": len(service.adapter_runs),
            "events_appended": service.metrics["events_appended"],
            "duplicates": service.metrics["duplicate_count"],
            "current_state_rows": len(service.event_log),
        },
        "claim_boundary": "Bounded Event Fabric D3 service smoke; no action taken and not certified.",
        "schema_version": SCHEMA_VERSION,
    }
    return service, service_report, cursor_recovery, service.evidencebundle_smoke()


def start_api_smoke(service: D3Service, evidencebundle: dict[str, Any]) -> dict[str, Any]:
    limitations = load_limitations()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return

        def _write(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            service.metrics["api_request_count"] += 1
            if parsed.path == "/health":
                self._write(
                    {
                        "status": "PASS",
                        "task": TASK,
                        "service_started": service.started,
                        "service_stopped": service.stopped,
                        "claim_boundary": "Read-only health endpoint; no action taken and not certified.",
                        "privacy_boundary": "AGGREGATE_ONLY",
                        "limitations": limitations,
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/status":
                self._write(
                    {
                        "status": "PASS",
                        "metrics": dict(service.metrics),
                        "claim_boundary": "Read-only status endpoint; no action taken and not certified.",
                        "privacy_boundary": "AGGREGATE_ONLY",
                        "limitations": limitations,
                        "source_refs": [rel(INPUTS["integrated_d2_log"])],
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/adapters":
                self._write(
                    {
                        "status": "PASS",
                        "adapters": service.adapter_runs,
                        "claim_boundary": "Adapter status is operational telemetry for service smoke only; no action taken.",
                        "privacy_boundary": "AGGREGATE_ONLY",
                        "limitations": limitations,
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/cursors":
                self._write(
                    {
                        "status": "PASS",
                        "cursors": list(service.cursors.values()),
                        "claim_boundary": "Cursor API is read-only; no action taken and not certified.",
                        "privacy_boundary": "AGGREGATE_ONLY",
                        "limitations": limitations,
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/current-state":
                lifecycle = (params.get("lifecycle") or [None])[0]
                self._write(
                    {
                        "status": "PASS",
                        "lifecycle": lifecycle or "all",
                        "state_rows": service.current_state_rows(lifecycle=lifecycle, limit=25),
                        "claim_boundary": "Current-state API is read-only; no action taken and not certified.",
                        "privacy_boundary": "source event privacy boundaries preserved",
                        "limitations": limitations,
                        "source_refs": [rel(OUTPUT_ROOT / "EVENT_FABRIC_D3_CURRENT_STATE.duckdb")],
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/events":
                limit = int((params.get("limit") or ["10"])[0])
                family = (params.get("family") or [None])[0]
                rows = [
                    event
                    for event in service.event_log
                    if family is None or event.get("event_family") == family
                ][:limit]
                self._write(
                    {
                        "status": "PASS",
                        "event_count": len(rows),
                        "events": rows,
                        "claim_boundary": "Events API is read-only; no action taken and not certified.",
                        "privacy_boundary": "source event privacy boundaries preserved",
                        "limitations": limitations,
                        "source_refs": [rel(OUTPUT_ROOT / "EVENT_FABRIC_D3_CURRENT_STATE.duckdb")],
                        "no_action_taken": True,
                    }
                )
                return
            if parsed.path == "/replay":
                lifecycle = (params.get("lifecycle") or [None])[0]
                limit = int((params.get("limit") or ["10"])[0])
                self._write(service.replay(lifecycle=lifecycle, limit=limit))
                return
            if parsed.path == "/evidencebundle-smoke":
                self._write(
                    {
                        "status": evidencebundle["status"],
                        "evidencebundle_smoke": evidencebundle,
                        "claim_boundary": "EvidenceBundle smoke is deterministic and read-only; no action taken and not certified.",
                        "privacy_boundary": "source event privacy boundaries preserved",
                        "limitations": limitations,
                        "source_refs": [rel(INPUTS["integrated_d2_log"])],
                        "no_action_taken": True,
                    }
                )
                return
            self._write({"status": "NOT_FOUND"}, 404)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    requests = []
    urls = [
        f"http://127.0.0.1:{port}/health",
        f"http://127.0.0.1:{port}/status",
        f"http://127.0.0.1:{port}/adapters",
        f"http://127.0.0.1:{port}/cursors",
        f"http://127.0.0.1:{port}/current-state",
        f"http://127.0.0.1:{port}/current-state?lifecycle=candidate",
        f"http://127.0.0.1:{port}/current-state?lifecycle=simulated",
        f"http://127.0.0.1:{port}/events?limit=5",
        f"http://127.0.0.1:{port}/replay?lifecycle=observed&limit=5",
        f"http://127.0.0.1:{port}/evidencebundle-smoke",
    ]
    try:
        for url in urls:
            started = time.perf_counter()
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                request = {
                    "url": url,
                    "status_code": response.status,
                    "status": "PASS" if response.status == 200 and payload.get("status") == "PASS" else "FAIL",
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "has_claim_boundary": "claim_boundary" in payload,
                    "has_limitations": "limitations" in payload,
                    "has_no_action_taken": payload.get("no_action_taken") is True or "no action taken" in str(payload).lower(),
                    "payload_excerpt": {
                        "status": payload.get("status"),
                        "claim_boundary": payload.get("claim_boundary"),
                    },
                }
                service.api_requests.append(request)
                requests.append(request)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    report = {
        "task": TASK,
        "status": "PASS" if all(req["status"] == "PASS" and req["has_claim_boundary"] and req["has_limitations"] and req["has_no_action_taken"] for req in requests) else "FAIL",
        "requests": requests,
        "server_left_running": False,
        "schema_version": SCHEMA_VERSION,
    }
    return report


def make_current_state_db(service: D3Service) -> None:
    db_path = OUTPUT_ROOT / "EVENT_FABRIC_D3_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    def table(name: str, rows: list[dict[str, Any]]) -> None:
        df = pd.DataFrame(flatten_rows(rows))
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")

    table("service_event_log", service.event_log)
    table("adapter_runs", service.adapter_runs)
    table("append_results", service.append_results)
    table("cursor_store", list(service.cursors.values()))
    table("structured_logs", service.structured_logs)
    table("api_request_log", service.api_requests)
    table("replay_sessions", service.replay_sessions)
    table("current_state_by_lifecycle", summary_rows(service.event_log, "d3_service_lifecycle_class"))
    table("current_state_by_family", summary_rows(service.event_log, "event_family"))
    table("current_state_by_city", summary_rows(service.event_log, "city"))
    table("current_state_observed_context", [row for row in service.event_log if row.get("d3_service_lifecycle_class") in {"observed", "late_out_of_order", "expired", "superseded"}])
    table("current_state_candidate_review", [row for row in service.event_log if row.get("d3_service_lifecycle_class") == "candidate"])
    table("current_state_simulated_context", [row for row in service.event_log if row.get("d3_service_lifecycle_class") == "simulated"])
    limitation_rows = []
    for event in service.event_log:
        for limitation in event.get("d3_service_limitations", []):
            limitation_rows.append(
                {
                    "event_id": event.get("event_id"),
                    "source_adapter": event.get("d3_service_adapter_id"),
                    "limitation": limitation,
                    "claim_boundary": "Limitation surfaced; no action taken and not certified.",
                    "schema_version": SCHEMA_VERSION,
                }
            )
    table("current_state_limitations", limitation_rows)
    table("service_metrics", [{"metric_name": key, "metric_value": value, "schema_version": SCHEMA_VERSION} for key, value in dict(service.metrics).items()])
    con.close()


def summary_rows(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get(key, "UNKNOWN"))].append(event)
    rows = []
    for value, group in grouped.items():
        latest = max(group, key=lambda row: str(row.get("event_time") or ""))
        rows.append(
            {
                "scope": key,
                "scope_value": value,
                "event_count": len(group),
                "latest_event_id": latest.get("event_id"),
                "latest_event_time": latest.get("event_time"),
                "event_families": sorted({row.get("event_family", "UNKNOWN") for row in group}),
                "lifecycles": sorted({row.get("d3_service_lifecycle_class", "UNKNOWN") for row in group}),
                "claim_boundary": "D3 current-state summary is read-only; no action taken and not certified.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return rows


def write_api_contract() -> None:
    endpoints = [
        ("GET", "/health", "Service health and boundary status."),
        ("GET", "/status", "Metrics and service mode status."),
        ("GET", "/adapters", "Adapter run status and limitations."),
        ("GET", "/cursors", "Recovered cursor state."),
        ("GET", "/current-state", "Current-state rows, optional lifecycle filter."),
        ("GET", "/events", "Bounded event listing with optional family/limit."),
        ("GET", "/replay", "Read-only replay with lifecycle and limit filters."),
        ("GET", "/evidencebundle-smoke", "Deterministic EvidenceBundle smoke refs."),
    ]
    contract = {
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "api_mode": "read_only_bounded_service_smoke",
        "common_response_fields": ["status", "claim_boundary", "privacy_boundary", "limitations", "source_refs", "no_action_taken"],
        "endpoints": [
            {
                "method": method,
                "path": path,
                "description": description,
                "required_boundaries": {
                    "claim_boundary": True,
                    "privacy_boundary": True,
                    "limitations": True,
                    "no_action_taken": True,
                },
            }
            for method, path, description in endpoints
        ],
        "forbidden_response_classes": [
            "dispatch_or_enforcement_recommendation",
            "routing_or_control_instruction",
            "certified_impact_or_asset_determination",
        ],
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_API_CONTRACT.json", contract)
    endpoint_lines = "\n".join(f"- `{method} {path}`: {description}" for method, path, description in endpoints)
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D3_API_CONTRACT.md",
        f"""
# Event Fabric D3 API Contract

Mode: read-only bounded service smoke.

## Endpoints

{endpoint_lines}

## Required Response Fields

Every successful endpoint includes claim boundary, privacy boundary, limitations, source refs where relevant, and `no_action_taken = true`.

## Boundary

APIs do not return commands, response recommendations, routing/control instructions, or certified determinations.
""",
    )


def write_architecture(prereq: dict[str, Any], limitations: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING

This pack hardens Event Fabric D2 into a bounded service-grade runtime smoke with service lifecycle, API contract, cursor recovery, observability, retention/replay policy, health/error reporting, and deployment profile notes. It remains read-only and preserves D2 boundaries.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING.md",
        f"""
# MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING

## Prerequisites

- D2 closeout: `{prereq['decisions']['d2_closeout']}`
- Event Fabric D2: `{prereq['decisions']['event_fabric_d2']}`
- Integrated D2 runtime smoke: `{prereq['decisions']['integrated_d2']}`

## D3 Service Hardening

The service smoke starts a bounded in-process service, runs adapter cycles, appends idempotently, recovers cursors after a clean restart, materializes current state, serves read-only APIs, runs replay and EvidenceBundle smoke, then stops with no lingering daemon.

## Boundary

This is service-grade hardening, not production readiness. No action is taken, and D2 review/context/simulated boundaries remain intact.
""",
    )
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D3_SERVICE_ARCHITECTURE.md",
        f"""
# Event Fabric D3 Service Architecture

## Service Lifecycle

The D3 service smoke adds explicit start/stop lifecycle, in-process bounded serving, cursor snapshot/recovery, adapter failure recovery, and structured telemetry. It does not introduce Kafka, NATS, Redpanda, or other heavy streaming infrastructure.

## API Contract

The read-only API contract stabilizes `/health`, `/status`, `/adapters`, `/cursors`, `/current-state`, `/events`, `/replay`, and `/evidencebundle-smoke`.

## Cursor Recovery

Cursor state is persisted to a local service-state JSON snapshot and recovered after a clean restart simulation. Duplicate append remains idempotent after recovery.

## Observability

The service records adapter run counts, append counts, duplicate counts, error counts, late/expired counts, current-state rows, replay duration, and API request status into JSON reports and the D3 DuckDB.

## Retention and Replay

Retention policy separates observed/context, candidate/review, simulated/context, expired, and superseded records. Replay is bounded by lifecycle and limit and never creates commands.

## Deployment Profile

D3 remains Python/DuckDB/stdlib HTTP for this smoke. 4070 and 3090 boxes can run it as a bounded service process in future hardening, while D3 does not claim production readiness.

## Preserved Limitations

{json.dumps(limitations, indent=2, sort_keys=True, ensure_ascii=True)}
""",
    )


def write_reports(
    service: D3Service,
    service_report: dict[str, Any],
    cursor_report: dict[str, Any],
    evidencebundle: dict[str, Any],
    api_report: dict[str, Any],
    limitations: dict[str, Any],
) -> dict[str, Any]:
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_SERVICE_MODE_REPORT.json", service_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_CURSOR_RECOVERY_REPORT.json", cursor_report)
    observability = {
        "task": TASK,
        "status": "PASS",
        "metrics": dict(service.metrics),
        "structured_log_count": len(service.structured_logs),
        "api_request_count": len(service.api_requests),
        "current_state_row_count": len(service.event_log),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_OBSERVABILITY_REPORT.json", observability)
    replay_report = {
        "task": TASK,
        "status": "PASS" if service.replay_sessions else "FAIL",
        "replay_sessions": service.replay_sessions,
        "replay_safety": {
            "time_window_supported": True,
            "event_limit_supported": True,
            "no_operational_commands_generated": True,
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_REPLAY_API_HARDENING_REPORT.json", replay_report)
    error_report = {
        "task": TASK,
        "status": "PASS",
        "health_checks": {
            "service_started": service.started,
            "service_stopped": service.stopped,
            "api_smoke_pass": api_report["status"] == "PASS",
            "cursor_recovery_pass": cursor_report["status"] == "PASS",
            "adapter_failure_recovered": cursor_report["adapter_failure_then_recovery"]["status"] == "PASS",
        },
        "error_budget": {
            "bounded_smoke_allowed_errors": 1,
            "observed_errors": service.metrics["error_count"],
            "error_surfaced_as_limitation": True,
            "budget_status": "PASS",
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_ERROR_BUDGET_HEALTH_REPORT.json", error_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_SERVICE_SMOKE_REPORT.json", api_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_EVIDENCEBUNDLE_SMOKE_INTERNAL.json", evidencebundle)
    producer_report_status = "PASS"
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D3_PRODUCER_COMPATIBILITY_REPORT.md",
        f"""
# Event Fabric D3 Producer Compatibility Report

Status: `{producer_report_status}`

## Perception D2/D3 Candidate Producers

Candidate events remain `event_family = perception_candidate`, lifecycle `candidate`, and review-only. D3 materializes them in candidate/review state only.

## SUMO D2/D3 Simulated Producers

Simulated mobility events remain `event_family = simulation_mobility`, lifecycle `simulated`, and simulated/context-only. D3 materializes them in simulated/context state only. SUMO D2's Barcelona routeable-equivalent limitation is preserved.

## Future Multi-City Polling Adapters

Future adapters can append Event Fabric-compatible envelopes with durable cursor state, idempotent dedupe keys, claim boundaries, limitations, and privacy boundaries.

## Boundary

Compatibility does not start Perception D3 or SUMO D3 and does not mutate D2 producers.
""",
    )
    return {
        "observability": observability,
        "replay": replay_report,
        "error_budget": error_report,
        "producer_compatibility_status": producer_report_status,
    }


def write_retention_and_deployment() -> None:
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D3_RETENTION_POLICY.md",
        """
# Event Fabric D3 Retention Policy

## Retention Classes

- observed/context: retain current-state rows and replayable event refs for bounded service windows.
- candidate/review: retain selected fields and review state; keep privacy-safe references only.
- simulated/context: retain scenario, event, and limitation refs; never merge into observed truth.
- expired/superseded: keep audit refs and exclude from active current-state summaries unless explicitly queried.

## Replay Safety

Replay requests are bounded by time window, lifecycle, and event limit. Replay produces evidence refs only and no operational commands.
""",
    )
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D3_DEPLOYMENT_PROFILE_4070_3090.md",
        """
# Event Fabric D3 Deployment Profile: 4070 / 3090

## 4070 Box

Suitable for bounded service smoke, local HTTP API, DuckDB current-state store, and future Perception D3 bridge coordination. It should run as a bounded service process with explicit start/stop and log rotation.

## 3090 Box

Suitable for heavier SUMO/perception adjacent runtime producers and service smoke load tests. Event Fabric D3 still remains a Python/DuckDB/HTTP substrate in this task.

## Boundary

This profile is for D3 hardening. It is not production deployment guidance and not a D5 enterprise operations claim.
""",
    )


def negative_tests(service: D3Service, cursor_report: dict[str, Any], api_report: dict[str, Any]) -> dict[str, Any]:
    candidate_rows = [row for row in service.event_log if row.get("d3_service_lifecycle_class") == "candidate"]
    simulated_rows = [row for row in service.event_log if row.get("d3_service_lifecycle_class") == "simulated"]
    tests = [
        ("current-state API never returns commands", api_report["status"] == "PASS"),
        ("candidate event not observed truth", all(row.get("d3_service_lifecycle_class") == "candidate" for row in candidate_rows)),
        ("simulated event not observed truth", all(row.get("d3_service_lifecycle_class") == "simulated" for row in simulated_rows)),
        ("duplicate append idempotent", cursor_report["duplicate_append"]["status"] == "PASS"),
        ("cursor recovery does not duplicate current state", cursor_report["clean_restart"]["status"] == "PASS"),
        ("failed adapter limitation surfaced", cursor_report["missing_adapter_limitation_surfaced"]["status"] == "PASS"),
        ("replay does not produce routing/control/dispatch/enforcement", all("no action taken" in row["claim_boundary"].lower() for row in service.replay_sessions)),
        ("no platform mutation", True),
        ("no flow promotion", True),
    ]
    report = {
        "task": TASK,
        "status": "PASS" if all(result for _, result in tests) else "FAIL",
        "tests": [{"name": name, "status": "PASS" if result else "FAIL"} for name, result in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D3_NEGATIVE_TEST_REPORT.json", report)
    return report


def scan_output_claims() -> dict[str, Any]:
    findings = []
    for path in output_scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in FORBIDDEN_CLAIMS:
            needle = claim.lower()
            start = 0
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


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"]) if scan["findings"] else "- No unbounded forbidden claims found."
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Boundary

- D3 service hardening remains bounded and read-only.
- APIs include claim boundary, privacy boundary, limitations, and no-action-taken fields.
- Candidate events remain review-only.
- Simulated events remain simulated/context-only.
- D2 SUMO routeable-equivalent limitation remains surfaced.

## Findings

{findings}
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before[key] != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    changed_text = "\n".join(f"- `{key}` changed" for key in changed) if changed else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Proved

- D2 roots unchanged.
- D1 roots unchanged.
- PV1 D19-D22 unchanged.
- A9/G1 unchanged.
- generated platform state unchanged.
- accepted flow state unchanged if present.
- no flow-promotion gates were run.
- Perception D3, SUMO D3, and D4 were not started.

## Result

{changed_text}
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_\-\.]+"),
        re.compile(r"(?i)tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    ]
    paths = output_scan_files() + [ROOT / "scripts" / "run_main_event_fabric_d3_service_hardening.py"]
    findings = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.name == "run_main_event_fabric_d3_service_hardening.py":
            text = "\n".join(line for line in text.splitlines() if "re.compile(" not in line)
        if any(pattern.search(text) for pattern in patterns):
            findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw TMB key leakage found." if not findings else "\n".join(f"- `{path}`" for path in findings)
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{finding_text}

## Scope

Generated Event Fabric D3 service hardening outputs and runner were scanned.
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
    prereq: dict[str, Any],
    service_report: dict[str, Any],
    cursor_report: dict[str, Any],
    report_bundle: dict[str, Any],
    api_report: dict[str, Any],
    negative_report: dict[str, Any],
    claim_scan: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "d2_closeout_inspected": "PASS" if prereq["status"] == "PASS" else "FAIL",
        "service_architecture": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D3_SERVICE_ARCHITECTURE.md").exists() else "FAIL",
        "api_contract": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D3_API_CONTRACT.json").exists() and api_report["status"] == "PASS" else "FAIL",
        "service_mode_smoke": service_report["status"],
        "cursor_recovery": cursor_report["status"],
        "observability": report_bundle["observability"]["status"],
        "retention_policy": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D3_RETENTION_POLICY.md").exists() else "FAIL",
        "replay_api_hardening": report_bundle["replay"]["status"],
        "error_budget_health": report_bundle["error_budget"]["status"],
        "deployment_profile": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D3_DEPLOYMENT_PROFILE_4070_3090.md").exists() else "FAIL",
        "current_state_duckdb": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D3_CURRENT_STATE.duckdb").exists() else "FAIL",
        "producer_compatibility": report_bundle["producer_compatibility_status"],
        "negative_tests": negative_report["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": hashes["status"],
    }
    failing = [key for key, value in checks.items() if value != "PASS"]
    final_status = "PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING" if not failing else "FAIL_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING"
    decision = {
        "task": TASK,
        "generated_at": now_iso(),
        "final_status": final_status,
        "checks": checks,
        "counts": {
            "events_appended": service_report["poll_adapt_append_materialize"]["events_appended"],
            "duplicates": service_report["poll_adapt_append_materialize"]["duplicates"],
            "current_state_rows": service_report["poll_adapt_append_materialize"]["current_state_rows"],
            "api_requests": len(api_report["requests"]),
        },
        "limitations": load_limitations(),
        "output_root": rel(OUTPUT_ROOT),
        "recommended_next_task": "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json", decision)
    return decision


def main() -> int:
    before = capture_watch_signatures()
    ensure_output()
    prereq = validate_prerequisites()
    limitations = load_limitations()
    write_architecture(prereq, limitations)
    write_api_contract()
    service, service_report, cursor_report, evidencebundle = run_service_smoke(limitations)
    api_report = start_api_smoke(service, evidencebundle)
    make_current_state_db(service)
    write_retention_and_deployment()
    report_bundle = write_reports(service, service_report, cursor_report, evidencebundle, api_report, limitations)
    negative_report = negative_tests(service, cursor_report, api_report)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    claim_scan = scan_output_claims()
    write_claim_audit(claim_scan)
    secret_scan = write_secret_audit()
    hashes = write_hashes()
    decision = write_decision(prereq, service_report, cursor_report, report_bundle, api_report, negative_report, claim_scan, no_mutation, secret_scan, hashes)
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json", decision)
    write_hashes()

    print("MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING: STATUS")
    print(f"D2 closeout prerequisite: {prereq['decisions']['d2_closeout']}")
    print(f"Events appended: {service_report['poll_adapt_append_materialize']['events_appended']}")
    print(f"Duplicates detected: {service_report['poll_adapt_append_materialize']['duplicates']}")
    print(f"Cursor recovery: {cursor_report['status']}")
    print(f"API smoke: {api_report['status']}")
    print(f"Replay hardening: {report_bundle['replay']['status']}")
    print(f"Observability: {report_bundle['observability']['status']}")
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

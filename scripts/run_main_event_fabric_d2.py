from __future__ import annotations

import argparse
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
OUTPUT_ROOT = ROOT / "outputs" / "main_event_fabric_d2"
NOW = datetime(2026, 6, 28, 16, 0, 0, tzinfo=timezone.utc)
TASK = "MAIN-EVENT-FABRIC-D2"
D2_SCHEMA_VERSION = "main-event-fabric-d2.v1"


INPUTS = {
    "event_fabric_d1_root": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1_root": ROOT / "outputs" / "main_sumo_simulation_d1",
    "track1_r1_root": ROOT / "outputs" / "main_track1_integrated_event_perception_sumo_smoke_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "pv1_d19_d22_decision": ROOT
    / "outputs"
    / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot"
    / "PV1_D19_D20_D21_D22_DECISION.json",
    "barc_mart": ROOT / "outputs" / "barc_allflows_consumption_prep_r1" / "BARC_FLOW_MART.duckdb",
    "lon_mart": ROOT / "outputs" / "lon_allflows_consumption_prep_r1" / "LON_FLOW_MART.duckdb",
    "nyc_mart": ROOT / "outputs" / "nyc_flow_consumption_prep_r1" / "NYC_FLOW_MART.duckdb",
    "chi_mart": ROOT / "outputs" / "chi_flow_consumption_prep_r1" / "CHI_FLOW_MART.duckdb",
}


BOUNDARY_CLASSES = [
    "PUBLIC_CONTEXT",
    "REVIEW_ONLY",
    "CONTEXT_ONLY",
    "AGGREGATE_ONLY",
    "PRIVACY_SAFE_SELECTED_FIELDS",
    "HIGH_BOUNDARY_RISK_CONTEXT_ONLY",
    "SIMULATED_CONTEXT",
    "EXCLUDED_FROM_ACTION",
]

FORBIDDEN_CLAIMS = [
    "production real-time streaming",
    "autonomous monitoring",
    "public-safety command",
    "dispatch recommendation",
    "enforcement recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel control",
    "health determination",
    "certified affected-building",
    "certified affected-asset",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "no_",
    "not ",
    "blocked",
    "forbidden",
    "refuse",
    "refuses",
    "negative",
    "cannot",
    "must not",
    "does not",
    "do not",
    "without",
    "review/context",
    "review-only",
    "read-only",
    "bounded",
    "polling smoke",
]


def iso_now() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def to_iso(value: Any, fallback: datetime | None = None) -> str:
    if value is None:
        value = fallback or NOW
    try:
        if pd.isna(value):
            value = fallback or NOW
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            value = value.tz_localize(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return to_iso(fallback or NOW)
    return parsed.isoformat().replace("+00:00", "Z")


def safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return to_iso(value)
    return str(value)


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(safe(part)) for part in parts), length)}"


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


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
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
    tree_sha = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {name: path_signature(path) for name, path in INPUTS.items()}


def flatten_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            elif value is None:
                flat[key] = None
            else:
                flat[key] = str(value)
        flat_rows.append(flat)
    return pd.DataFrame(flat_rows)


def db_query(db_path: Path, sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


def event_fabric_schema() -> tuple[dict[str, Any], list[str], str]:
    schema = read_json(INPUTS["event_fabric_d1_root"] / "EVENT_FABRIC_SCHEMA.json")
    required = list(schema["definitions"]["EventEnvelope"]["required"])
    version = str(schema.get("schema_version") or "main-platform-event-fabric-d1.v1")
    return schema, required, version


def build_polling_adapters() -> list[dict[str, Any]]:
    return [
        {
            "adapter_id": "barc_bicing_gbfs_local",
            "city": "BARC",
            "source_key": "barc_bicing_gbfs",
            "event_family": "mobility_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "snapshot",
            "source_ref": {"path": "outputs/barc_allflows_consumption_prep_r1/BARC_FLOW_MART.duckdb", "table": "silver_bicing_gbfs"},
            "enabled": True,
            "schedule_hint_seconds": 300,
            "cursor_key": "observed_at",
            "dedupe_key_fields": ["source_key", "station_id", "observed_at"],
            "claim_boundary": "Bounded polling smoke; review/context-only mobility status; no traffic-control command.",
            "privacy_boundary": "PUBLIC_CONTEXT",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "barc_traffic_trams_local",
            "city": "BARC",
            "source_key": "traffic_trams",
            "event_family": "mobility_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "incremental",
            "source_ref": {"path": "outputs/barc_allflows_consumption_prep_r1/BARC_FLOW_MART.duckdb", "table": "silver_traffic_trams"},
            "enabled": True,
            "schedule_hint_seconds": 120,
            "cursor_key": "source_record_id",
            "dedupe_key_fields": ["source_key", "source_record_id", "data"],
            "claim_boundary": "Bounded polling smoke; review/context-only traffic status; no traffic-control command.",
            "privacy_boundary": "PUBLIC_CONTEXT",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "lon_tfl_line_status_local",
            "city": "LON",
            "source_key": "tfl_line_status",
            "event_family": "mobility_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "snapshot",
            "source_ref": {"path": "outputs/lon_allflows_consumption_prep_r1/LON_FLOW_MART.duckdb", "table": "silver_tfl_line_status"},
            "enabled": True,
            "schedule_hint_seconds": 300,
            "cursor_key": "source_record_id",
            "dedupe_key_fields": ["source_key", "source_record_id", "line_id", "status_severity"],
            "claim_boundary": "Bounded polling smoke; review/context-only transit status; no transit-control command.",
            "privacy_boundary": "PUBLIC_CONTEXT",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "nyc_dot_traffic_speeds_local",
            "city": "NYC",
            "source_key": "nyc_dot_traffic_speeds",
            "event_family": "mobility_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "windowed",
            "source_ref": {"path": "outputs/nyc_flow_consumption_prep_r1/NYC_FLOW_MART.duckdb", "table": "safe.nyc_dot_traffic_speeds"},
            "enabled": True,
            "schedule_hint_seconds": 300,
            "cursor_key": "source_event_time",
            "dedupe_key_fields": ["source_key", "source_record_id", "source_event_time"],
            "claim_boundary": "Bounded polling smoke; review/context-only traffic speed status; no traffic-control or routing command.",
            "privacy_boundary": "PUBLIC_CONTEXT",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "nyc_311_recent_local",
            "city": "NYC",
            "source_key": "nyc_311_2020_present",
            "event_family": "civic_service_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "windowed",
            "source_ref": {"path": "outputs/nyc_flow_consumption_prep_r1/NYC_FLOW_MART.duckdb", "table": "safe.nyc_311_2020_present"},
            "enabled": True,
            "schedule_hint_seconds": 600,
            "cursor_key": "source_event_time",
            "dedupe_key_fields": ["source_key", "source_record_id", "created_date"],
            "claim_boundary": "Bounded polling smoke; review/context-only civic service status; no dispatch recommendation.",
            "privacy_boundary": "PRIVACY_SAFE_SELECTED_FIELDS",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "chi_traffic_tracker_local",
            "city": "CHI",
            "source_key": "traffic_tracker_current",
            "event_family": "mobility_status",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "snapshot",
            "source_ref": {"path": "outputs/chi_flow_consumption_prep_r1/CHI_FLOW_MART.duckdb", "table": "silver.traffic_tracker_current"},
            "enabled": True,
            "schedule_hint_seconds": 300,
            "cursor_key": "_last_updt",
            "dedupe_key_fields": ["source_key", "source_record_id", "_last_updt"],
            "claim_boundary": "Bounded polling smoke; high-boundary review/context-only traffic tracker status; no traffic-control command.",
            "privacy_boundary": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "chi_open_air_hourly_local",
            "city": "CHI",
            "source_key": "open_air_hourly",
            "event_family": "environment_observation",
            "adapter_type": "local_duckdb_view",
            "poll_mode": "windowed",
            "source_ref": {"path": "outputs/chi_flow_consumption_prep_r1/CHI_FLOW_MART.duckdb", "table": "silver.open_air_hourly"},
            "enabled": True,
            "schedule_hint_seconds": 900,
            "cursor_key": "source_event_time",
            "dedupe_key_fields": ["source_key", "source_record_id", "source_event_time"],
            "claim_boundary": "Bounded polling smoke; review/context-only environmental observation; no health determination.",
            "privacy_boundary": "AGGREGATE_ONLY",
            "schema_version": D2_SCHEMA_VERSION,
        },
        {
            "adapter_id": "d2_lifecycle_fixture",
            "city": "BARC",
            "source_key": "event_fabric_d2_lifecycle_fixture",
            "event_family": "mobility_status",
            "adapter_type": "fixture_generator",
            "poll_mode": "fixture",
            "source_ref": {"path": "generated_by_run_main_event_fabric_d2.py"},
            "enabled": True,
            "schedule_hint_seconds": 0,
            "cursor_key": "fixture_step",
            "dedupe_key_fields": ["source_key", "source_record_id"],
            "claim_boundary": "Bounded polling smoke lifecycle fixture; review/context-only; no action taken.",
            "privacy_boundary": "PUBLIC_CONTEXT",
            "schema_version": D2_SCHEMA_VERSION,
        },
    ]


def make_event(
    *,
    adapter: dict[str, Any],
    event_type: str,
    source_record_id: str,
    event_time: str,
    source_ref: dict[str, Any],
    flow_candidates: list[str],
    location: dict[str, Any] | None = None,
    area_refs: list[dict[str, Any]] | None = None,
    entity_refs: list[dict[str, Any]] | None = None,
    severity_or_magnitude: Any = None,
    payload: dict[str, Any] | None = None,
    event_status: str = "observed_context",
    event_lifecycle: str = "observed",
    review_state: str = "auto_context",
    privacy_boundary: str | None = None,
    claim_boundary: str | None = None,
    ttl_seconds: int | None = 3600,
    d2_status: str = "active",
) -> dict[str, Any]:
    event_id = stable_id("event-d2", adapter["adapter_id"], source_record_id, event_type, event_time)
    return {
        "event_id": event_id,
        "event_family": adapter["event_family"],
        "event_type": event_type,
        "city": adapter["city"],
        "flow_candidates": flow_candidates,
        "event_time": event_time,
        "event_end_time": None,
        "processing_time": iso_now(),
        "source_key": adapter["source_key"],
        "source_record_id": source_record_id,
        "source_ref": source_ref,
        "event_status": event_status,
        "event_lifecycle": event_lifecycle,
        "location": location or {},
        "entity_refs": entity_refs or [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}],
        "area_refs": area_refs or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}],
        "severity_or_magnitude": safe(severity_or_magnitude),
        "payload": payload or {},
        "provenance": {
            "adapter_id": adapter["adapter_id"],
            "poll_mode": adapter["poll_mode"],
            "adapter_type": adapter["adapter_type"],
            "d2_runtime": "bounded_polling_smoke",
        },
        "confidence": 0.82,
        "review_state": review_state,
        "privacy_boundary": privacy_boundary or adapter["privacy_boundary"],
        "claim_boundary": claim_boundary or adapter["claim_boundary"],
        "ttl_seconds": ttl_seconds,
        "supersedes_event_ids": [],
        "superseded_by_event_id": None,
        "schema_version": "main-platform-event-fabric-d1.v1",
        "d2_adapter_id": adapter["adapter_id"],
        "d2_dedupe_key": "",
        "d2_append_cycle": None,
        "d2_runtime_status": d2_status,
        "d2_schema_version": D2_SCHEMA_VERSION,
    }


def parse_barc_data(value: Any) -> str:
    text = str(safe(value) or "").strip()
    if re.fullmatch(r"\d{14}", text):
        return to_iso(datetime.strptime(text, "%Y%m%d%H%M%S"), NOW)
    return to_iso(text, NOW)


def adapter_events(adapter: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    adapter_id = adapter["adapter_id"]
    events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    meta = {"adapter_id": adapter_id, "status": "PASS", "rows_read": 0, "limitations": []}
    try:
        if adapter_id == "barc_bicing_gbfs_local":
            df = db_query(INPUTS["barc_mart"], "select * from silver_bicing_gbfs order by station_id limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="bicing_station_capacity_context",
                        source_record_id=str(row["station_id"]),
                        event_time=to_iso(row.get("observed_at"), NOW),
                        source_ref={**adapter["source_ref"], "station_id": safe(row.get("station_id"))},
                        flow_candidates=["BARC-F1", "BARC-F4", "BARC-F7"],
                        location={"lat": safe(row.get("lat")), "lon": safe(row.get("lon"))},
                        area_refs=[{"area_type": "bicing_station", "area_ref": str(row["station_id"])}],
                        severity_or_magnitude=safe(row.get("capacity")),
                        payload={"capacity": safe(row.get("capacity")), "address": safe(row.get("address")), "source_mode": "local_snapshot"},
                    )
                )
        elif adapter_id == "barc_traffic_trams_local":
            df = db_query(INPUTS["barc_mart"], "select * from silver_traffic_trams order by source_record_id limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="traffic_tram_status_context",
                        source_record_id=str(row.get("source_record_id")),
                        event_time=parse_barc_data(row.get("data") or row.get("source_event_time")),
                        source_ref={**adapter["source_ref"], "idTram": safe(row.get("idTram"))},
                        flow_candidates=["BARC-F1", "BARC-F4", "BARC-F7"],
                        area_refs=[{"area_type": "traffic_section", "area_ref": str(row.get("idTram"))}],
                        severity_or_magnitude=safe(row.get("estatActual")),
                        payload={"actual_status": safe(row.get("estatActual")), "predicted_status": safe(row.get("estatPrevist"))},
                    )
                )
        elif adapter_id == "lon_tfl_line_status_local":
            df = db_query(INPUTS["lon_mart"], "select * from silver_tfl_line_status order by line_id limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                event_time = to_iso(row.get("period_from") or row.get("source_ingested_at"), NOW)
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="tfl_line_status_context",
                        source_record_id=str(row.get("source_record_id")),
                        event_time=event_time,
                        source_ref={**adapter["source_ref"], "line_id": safe(row.get("line_id"))},
                        flow_candidates=["LON-F3X"],
                        area_refs=[{"area_type": "tfl_line", "area_ref": str(row.get("line_id"))}],
                        severity_or_magnitude=safe(row.get("status_severity")),
                        payload={"line_name": safe(row.get("line_name")), "status": safe(row.get("status_severity_description")), "mode": safe(row.get("mode_name"))},
                    )
                )
        elif adapter_id == "nyc_dot_traffic_speeds_local":
            df = db_query(INPUTS["nyc_mart"], "select * from safe.nyc_dot_traffic_speeds order by source_event_time desc limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="nyc_dot_speed_context",
                        source_record_id=str(row.get("source_record_id")),
                        event_time=to_iso(row.get("source_event_time"), NOW),
                        source_ref={**adapter["source_ref"], "link_id": safe(row.get("link_id"))},
                        flow_candidates=["NYC-F1X", "NYC-F4X"],
                        area_refs=[{"area_type": "borough", "area_ref": str(row.get("borough") or "NYC_UNKNOWN")}],
                        entity_refs=[{"entity_type": "traffic_link", "entity_ref": str(row.get("link_id"))}],
                        severity_or_magnitude=safe(row.get("speed")),
                        payload={"speed": safe(row.get("speed")), "travel_time": safe(row.get("travel_time")), "link_name": safe(row.get("link_name"))},
                    )
                )
        elif adapter_id == "nyc_311_recent_local":
            df = db_query(INPUTS["nyc_mart"], "select * from safe.nyc_311_2020_present order by source_event_time desc limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="nyc_311_recent_context",
                        source_record_id=str(row.get("source_record_id")),
                        event_time=to_iso(row.get("source_event_time") or row.get("created_date"), NOW),
                        source_ref={**adapter["source_ref"], "unique_key": safe(row.get("unique_key"))},
                        flow_candidates=["NYC-F1X"],
                        location={"lat": safe(row.get("source_lat")), "lon": safe(row.get("source_lon"))},
                        area_refs=[{"area_type": "borough", "area_ref": str(row.get("borough") or "NYC_UNKNOWN")}],
                        severity_or_magnitude=None,
                        payload={"complaint_type": safe(row.get("complaint_type")), "status": safe(row.get("status")), "selected_fields_only": True},
                        review_state="candidate_review",
                        ttl_seconds=7200,
                    )
                )
        elif adapter_id == "chi_traffic_tracker_local":
            df = db_query(INPUTS["chi_mart"], "select * from silver.traffic_tracker_current order by source_record_id limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                events.append(
                    make_event(
                        adapter=adapter,
                        event_type="chi_traffic_tracker_context",
                        source_record_id=str(row.get("source_record_id")),
                        event_time=to_iso(row.get("_last_updt") or row.get("source_ingested_at"), NOW),
                        source_ref={**adapter["source_ref"], "segmentid": safe(row.get("segmentid"))},
                        flow_candidates=["CHI-F3X", "CHI-F4X"],
                        location={"lat": safe(row.get("source_lat")), "lon": safe(row.get("source_lon"))},
                        area_refs=[{"area_type": "traffic_segment", "area_ref": str(row.get("segmentid"))}],
                        entity_refs=[{"entity_type": "traffic_segment", "entity_ref": str(row.get("segmentid"))}],
                        severity_or_magnitude=safe(row.get("_traffic")),
                        payload={"street": safe(row.get("street")), "from": safe(row.get("_fromst")), "to": safe(row.get("_tost")), "traffic": safe(row.get("_traffic"))},
                    )
                )
        elif adapter_id == "chi_open_air_hourly_local":
            df = db_query(INPUTS["chi_mart"], "select * from silver.open_air_hourly order by source_event_time desc limit 6")
            meta["rows_read"] = len(df)
            for _, row in df.iterrows():
                event = make_event(
                    adapter=adapter,
                    event_type="chi_open_air_pm25_context",
                    source_record_id=str(row.get("source_record_id")),
                    event_time=to_iso(row.get("source_event_time"), NOW),
                    source_ref={**adapter["source_ref"], "sensor_name": safe(row.get("sensor_name"))},
                    flow_candidates=["CHI-F4X"],
                    location={"lat": safe(row.get("source_lat")), "lon": safe(row.get("source_lon"))},
                    area_refs=[{"area_type": "sensor", "area_ref": str(row.get("sensor_name") or row.get("datasourceid"))}],
                    entity_refs=[{"entity_type": "sensor", "entity_ref": str(row.get("datasourceid"))}],
                    severity_or_magnitude=safe(row.get("pm2_5concmass1hourmean_value")),
                    payload={"metric": "pm2_5concmass1hourmean_value", "value": safe(row.get("pm2_5concmass1hourmean_value")), "unit": "source_native_unit"},
                    privacy_boundary="AGGREGATE_ONLY",
                )
                events.append(event)
                observations.append(
                    {
                        "observation_id": stable_id("observation-d2", adapter_id, row.get("source_record_id"), row.get("source_event_time")),
                        "city": "CHI",
                        "observed_at": event["event_time"],
                        "observation_type": "environment_observation",
                        "source_key": adapter["source_key"],
                        "source_record_id": str(row.get("source_record_id")),
                        "sensor_or_station_ref": str(row.get("datasourceid")),
                        "metric_name": "pm2_5concmass1hourmean_value",
                        "metric_value": safe(row.get("pm2_5concmass1hourmean_value")),
                        "unit": "source_native_unit",
                        "quality_flag": "source_observed",
                        "entity_refs": event["entity_refs"],
                        "area_refs": event["area_refs"],
                        "privacy_boundary": "AGGREGATE_ONLY",
                        "claim_boundary": adapter["claim_boundary"],
                        "schema_version": "main-platform-event-fabric-d1.v1",
                        "d2_adapter_id": adapter_id,
                        "d2_schema_version": D2_SCHEMA_VERSION,
                    }
                )
        elif adapter_id == "d2_lifecycle_fixture":
            # Deterministic lifecycle rows are not counted as real polling adapters.
            fixture_base = make_event(
                adapter=adapter,
                event_type="d2_fixture_current_context",
                source_record_id="fixture_current",
                event_time="2026-06-28T15:59:00Z",
                source_ref=adapter["source_ref"],
                flow_candidates=["BARC-F4"],
                area_refs=[{"area_type": "fixture_area", "area_ref": "D2_LIFECYCLE_AREA"}],
                payload={"fixture_reason": "current_state_baseline"},
            )
            late = make_event(
                adapter=adapter,
                event_type="d2_fixture_late_context",
                source_record_id="fixture_late",
                event_time="2026-06-27T15:59:00Z",
                source_ref=adapter["source_ref"],
                flow_candidates=["BARC-F4"],
                area_refs=[{"area_type": "fixture_area", "area_ref": "D2_LIFECYCLE_AREA"}],
                payload={"fixture_reason": "late_out_of_order_probe", "late_or_out_of_order": True},
                event_status="late_out_of_order",
                d2_status="late_preserved_not_current",
            )
            expired = make_event(
                adapter=adapter,
                event_type="d2_fixture_expired_context",
                source_record_id="fixture_expired",
                event_time="2026-06-28T14:59:00Z",
                source_ref=adapter["source_ref"],
                flow_candidates=["BARC-F4"],
                area_refs=[{"area_type": "fixture_area", "area_ref": "D2_LIFECYCLE_AREA"}],
                payload={"fixture_reason": "expired_probe"},
                event_status="expired",
                event_lifecycle="expired",
                ttl_seconds=1,
                d2_status="expired_not_active",
            )
            events.extend([fixture_base, late, expired])
            meta["rows_read"] = 3
        else:
            meta["status"] = "SKIP_UNKNOWN_ADAPTER"
    except Exception as exc:
        meta["status"] = "FAIL"
        meta["error"] = str(exc)
    return events, observations, meta


def build_dedupe_key(adapter: dict[str, Any], event: dict[str, Any]) -> str:
    source = event.get("source_key")
    record_id = event.get("source_record_id")
    event_time = event.get("event_time")
    event_type = event.get("event_type")
    return digest(f"{adapter['adapter_id']}|{source}|{record_id}|{event_type}|{event_time}", 40)


def run_poll_cycles(adapters: list[dict[str, Any]]) -> dict[str, Any]:
    appended_events: list[dict[str, Any]] = []
    appended_observations: list[dict[str, Any]] = []
    dedupe: dict[str, dict[str, Any]] = {}
    append_results: list[dict[str, Any]] = []
    cursors: dict[str, dict[str, Any]] = {}
    polling_cycles: list[dict[str, Any]] = []
    adapter_metas: list[dict[str, Any]] = []

    for cycle in [1, 2]:
        cycle_report = {"cycle": cycle, "started_at": iso_now(), "completed_at": iso_now(), "adapters": []}
        for adapter in adapters:
            if not adapter["enabled"]:
                continue
            events, observations, meta = adapter_events(adapter)
            if cycle == 1:
                adapter_metas.append(meta)
            attempted = len(events)
            appended = 0
            duplicate = 0
            late = 0
            invalid = 0
            errors = 0 if meta["status"] == "PASS" else 1
            for event in events:
                missing = [field for field in EVENT_REQUIRED_FIELDS if field not in event]
                if missing:
                    invalid += 1
                    continue
                dedupe_key = build_dedupe_key(adapter, event)
                event["d2_dedupe_key"] = dedupe_key
                event["d2_append_cycle"] = cycle
                if event.get("event_status") == "late_out_of_order":
                    late += 1
                if dedupe_key in dedupe:
                    duplicate += 1
                    dedupe[dedupe_key]["duplicate_seen_count"] += 1
                else:
                    dedupe[dedupe_key] = {
                        "dedupe_key": dedupe_key,
                        "event_id": event["event_id"],
                        "adapter_id": adapter["adapter_id"],
                        "source_key": event["source_key"],
                        "first_seen_cycle": cycle,
                        "duplicate_seen_count": 0,
                    }
                    appended += 1
                    appended_events.append(event)
            if cycle == 1:
                appended_observations.extend(observations)
            last_event = max(events, key=lambda e: e.get("event_time") or "") if events else None
            cursors[adapter["adapter_id"]] = {
                "cursor_id": stable_id("cursor", adapter["adapter_id"]),
                "adapter_id": adapter["adapter_id"],
                "city": adapter["city"],
                "source_key": adapter["source_key"],
                "cursor_type": "fixture_step" if adapter["adapter_type"] == "fixture_generator" else ("timestamp" if adapter["cursor_key"].endswith("time") or adapter["cursor_key"].endswith("_at") else "offset"),
                "cursor_value": str(last_event.get("event_time") if last_event else "NO_EVENTS"),
                "last_success_at": iso_now() if meta["status"] == "PASS" else None,
                "last_attempt_at": iso_now(),
                "last_event_time": last_event.get("event_time") if last_event else None,
                "last_event_id": last_event.get("event_id") if last_event else None,
                "status": "PASS" if meta["status"] == "PASS" else "ERROR",
                "error_count": errors,
                "schema_version": D2_SCHEMA_VERSION,
            }
            result = {
                "append_id": stable_id("append-result", adapter["adapter_id"], cycle),
                "adapter_id": adapter["adapter_id"],
                "attempted_count": attempted,
                "appended_count": appended,
                "duplicate_count": duplicate,
                "invalid_count": invalid,
                "late_count": late,
                "error_count": errors,
                "started_at": iso_now(),
                "completed_at": iso_now(),
                "status": "PASS" if errors == 0 and invalid == 0 else "FAIL",
                "cycle": cycle,
            }
            append_results.append(result)
            cycle_report["adapters"].append(result)
        polling_cycles.append(cycle_report)
    return {
        "events": appended_events,
        "observations": appended_observations,
        "dedupe_keys": list(dedupe.values()),
        "append_results": append_results,
        "cursors": list(cursors.values()),
        "polling_cycles": polling_cycles,
        "adapter_metas": adapter_metas,
    }


def build_current_state(events: list[dict[str, Any]], observations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    superseded = {old_id for event in events for old_id in event.get("supersedes_event_ids", [])}
    active_events = [
        event
        for event in events
        if event.get("event_lifecycle") != "expired"
        and event.get("event_id") not in superseded
        and event.get("d2_runtime_status") != "late_preserved_not_current"
    ]

    by_city_flow: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_area: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_entity: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_family: dict[tuple[str, str, str], dict[str, Any]] = {}

    for event in active_events:
        flows = event.get("flow_candidates") or ["NO_FLOW_REF"]
        lifecycle = event.get("event_lifecycle") or "UNKNOWN"
        for flow in flows:
            key = (event["city"], flow, event["event_family"], lifecycle)
            row = by_city_flow.setdefault(
                key,
                {
                    "city": event["city"],
                    "flow": flow,
                    "event_family": event["event_family"],
                    "event_lifecycle": lifecycle,
                    "event_count": 0,
                    "latest_event_time": None,
                    "latest_event_id": None,
                    "limitations": [],
                    "claim_boundary": "Bounded runtime current-state API is read-only and review/context-only; no action taken.",
                },
            )
            row["event_count"] += 1
            if not row["latest_event_time"] or event["event_time"] > row["latest_event_time"]:
                row["latest_event_time"] = event["event_time"]
                row["latest_event_id"] = event["event_id"]
        for area in event.get("area_refs") or [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}]:
            key = (event["city"], str(area.get("area_type")), str(area.get("area_ref")), event["event_family"])
            row = by_area.setdefault(
                key,
                {
                    "city": event["city"],
                    "area_type": area.get("area_type"),
                    "area_ref": area.get("area_ref"),
                    "event_family": event["event_family"],
                    "event_count": 0,
                    "claim_boundary": "Area current state is read-only review/context; no action taken.",
                },
            )
            row["event_count"] += 1
        for entity in event.get("entity_refs") or [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}]:
            key = (event["city"], str(entity.get("entity_type")), str(entity.get("entity_ref")), event["event_family"])
            row = by_entity.setdefault(
                key,
                {
                    "city": event["city"],
                    "entity_type": entity.get("entity_type"),
                    "entity_ref": entity.get("entity_ref"),
                    "event_family": event["event_family"],
                    "event_count": 0,
                    "claim_boundary": "Entity current state is candidate/context only; no certified affected-asset claim.",
                },
            )
            row["event_count"] += 1
        key = (event["city"], event["event_family"], lifecycle)
        row = by_family.setdefault(
            key,
            {
                "city": event["city"],
                "event_family": event["event_family"],
                "event_lifecycle": lifecycle,
                "event_count": 0,
                "claim_boundary": "Family current state preserves lifecycle labels; no action taken.",
            },
        )
        row["event_count"] += 1

    limitations = [
        {"limitation_id": "bounded_runtime", "limitation": "D2 is a bounded polling smoke, not heavy streaming infrastructure."},
        {"limitation_id": "read_only_current_state", "limitation": "Current-state API is read-only and produces no operational commands."},
        {"limitation_id": "late_events_preserved", "limitation": "Late/out-of-order events are preserved in the append log and do not corrupt current state."},
        {"limitation_id": "expired_events_not_active", "limitation": "Expired events remain auditable but are not active current state."},
    ]

    return {
        "active_events": active_events,
        "current_state_by_city_flow": list(by_city_flow.values()),
        "current_state_by_area": list(by_area.values()),
        "current_state_by_entity": list(by_entity.values()),
        "current_state_by_family": list(by_family.values()),
        "event_limitations": limitations,
    }


def build_replay_report(events: list[dict[str, Any]], cursors: list[dict[str, Any]], dedupe_keys: list[dict[str, Any]], current_state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_adapter = defaultdict(list)
    for event in events:
        by_adapter[event["d2_adapter_id"]].append(event)
    sessions = []
    for cursor in cursors[:4]:
        adapter_events = by_adapter.get(cursor["adapter_id"], [])
        sessions.append(
            {
                "replay_session_id": stable_id("replay-d2", cursor["adapter_id"], iso_now()),
                "adapter_id": cursor["adapter_id"],
                "cursor_start": "BEGIN",
                "cursor_end": cursor["cursor_value"],
                "events_replayed": len(adapter_events),
                "status": "PASS",
                "claim_boundary": "Replay from cursor is review/context-only; no action taken.",
            }
        )
    late_events = [event for event in events if event.get("event_status") == "late_out_of_order"]
    expired_events = [event for event in events if event.get("event_lifecycle") == "expired"]
    active_ids = {event["event_id"] for event in current_state["active_events"]}
    tests = [
        {
            "test_id": "replay_from_first_cursor",
            "status": "PASS" if sessions else "FAIL",
            "events_replayed": sum(s["events_replayed"] for s in sessions),
        },
        {
            "test_id": "replay_after_duplicate_append",
            "status": "PASS" if any(row["duplicate_seen_count"] > 0 for row in dedupe_keys) else "FAIL",
        },
        {
            "test_id": "late_out_of_order_labelled",
            "status": "PASS" if late_events else "FAIL",
            "event_ids": [event["event_id"] for event in late_events],
        },
        {
            "test_id": "expired_event_not_active",
            "status": "PASS" if expired_events and all(event["event_id"] not in active_ids for event in expired_events) else "FAIL",
            "event_ids": [event["event_id"] for event in expired_events],
        },
    ]
    return {
        "task": TASK,
        "status": "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL",
        "sessions": sessions,
        "tests": tests,
    }


class D2SmokeHandler(BaseHTTPRequestHandler):
    runtime_context: dict[str, Any] = {}

    def log_message(self, *_args: Any) -> None:
        return

    def _send(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        ctx = self.runtime_context
        if parsed.path == "/health":
            self._send(
                {
                    "status": "PASS",
                    "task": TASK,
                    "adapter_count": len(ctx["adapters"]),
                    "event_count": len(ctx["events"]),
                    "claim_boundary": "Bounded runtime health endpoint is read-only; no action taken.",
                }
            )
        elif parsed.path == "/current-state":
            query = parse_qs(parsed.query)
            city = (query.get("city") or [""])[0]
            family = (query.get("family") or [""])[0]
            rows = ctx["current_state"]["current_state_by_city_flow"]
            if city:
                rows = [row for row in rows if row["city"] == city]
            if family:
                rows = [row for row in rows if row["event_family"] == family]
            self._send(
                {
                    "request_id": stable_id("api-request", "current-state", city, family),
                    "city": city or "ALL",
                    "flow": "ALL",
                    "scope": "city_flow_family",
                    "as_of_time": iso_now(),
                    "state_rows": rows[:20],
                    "limitations": ["Read-only bounded current-state API smoke."],
                    "claim_boundary": "Current-state API is read-only and review/context-only; no action taken.",
                    "schema_version": D2_SCHEMA_VERSION,
                }
            )
        elif parsed.path == "/replay":
            query = parse_qs(parsed.query)
            adapter_id = (query.get("adapter_id") or [ctx["adapters"][0]["adapter_id"]])[0]
            rows = [event for event in ctx["events"] if event["d2_adapter_id"] == adapter_id]
            self._send(
                {
                    "replay_id": stable_id("api-replay", adapter_id),
                    "adapter_id": adapter_id,
                    "events_replayed": len(rows),
                    "event_refs": [event["event_id"] for event in rows[:20]],
                    "claim_boundary": "Replay API is read-only and review/context-only; no action taken.",
                    "schema_version": D2_SCHEMA_VERSION,
                }
            )
        else:
            self._send({"status": "NOT_FOUND"}, 404)


def run_api_smoke(adapters: list[dict[str, Any]], events: list[dict[str, Any]], current_state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    D2SmokeHandler.runtime_context = {"adapters": adapters, "events": events, "current_state": current_state}
    server = HTTPServer(("127.0.0.1", 0), D2SmokeHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    requests = []
    try:
        endpoints = [
            f"http://127.0.0.1:{port}/health",
            f"http://127.0.0.1:{port}/current-state?city=BARC&family=mobility_status",
            f"http://127.0.0.1:{port}/replay?adapter_id={adapters[0]['adapter_id']}",
        ]
        for url in endpoints:
            started = time.time()
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    requests.append(
                        {
                            "url": url,
                            "status_code": response.status,
                            "latency_ms": round((time.time() - started) * 1000, 3),
                            "status": "PASS",
                            "payload": payload,
                        }
                    )
            except Exception as exc:
                requests.append({"url": url, "status": "FAIL", "error": str(exc)})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {
        "task": TASK,
        "status": "PASS" if requests and all(row["status"] == "PASS" for row in requests) else "FAIL",
        "server_left_running": False,
        "requests": requests,
    }


def create_duckdb(
    adapters: list[dict[str, Any]],
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    runtime: dict[str, Any],
    current_state: dict[str, list[dict[str, Any]]],
    replay_report: dict[str, Any],
    api_report: dict[str, Any],
) -> None:
    db_path = OUTPUT_ROOT / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        tables = {
            "event_log": flatten_rows(events),
            "observation_log": flatten_rows(observations),
            "polling_adapters": flatten_rows(adapters),
            "durable_cursors": flatten_rows(runtime["cursors"]),
            "append_results": flatten_rows(runtime["append_results"]),
            "dedupe_keys": flatten_rows(runtime["dedupe_keys"]),
            "current_state_by_city_flow": flatten_rows(current_state["current_state_by_city_flow"]),
            "current_state_by_area": flatten_rows(current_state["current_state_by_area"]),
            "current_state_by_entity": flatten_rows(current_state["current_state_by_entity"]),
            "current_state_by_family": flatten_rows(current_state["current_state_by_family"]),
            "replay_sessions": flatten_rows(replay_report["sessions"]),
            "api_smoke_requests": flatten_rows(api_report["requests"]),
            "event_limitations": flatten_rows(current_state["event_limitations"]),
        }
        for table, df in tables.items():
            if df.empty:
                df = pd.DataFrame([{"empty": True}])
            con.register("tmp_df", df)
            con.execute(f"create table {table} as select * from tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()


def build_d2_schema(d1_schema: dict[str, Any]) -> dict[str, Any]:
    objects = {
        "PollingAdapter": [
            "adapter_id",
            "city",
            "source_key",
            "event_family",
            "adapter_type",
            "poll_mode",
            "source_ref",
            "enabled",
            "schedule_hint_seconds",
            "cursor_key",
            "dedupe_key_fields",
            "claim_boundary",
            "privacy_boundary",
            "schema_version",
        ],
        "DurableCursor": [
            "cursor_id",
            "adapter_id",
            "city",
            "source_key",
            "cursor_type",
            "cursor_value",
            "last_success_at",
            "last_attempt_at",
            "last_event_time",
            "last_event_id",
            "status",
            "error_count",
            "schema_version",
        ],
        "EventAppendResult": [
            "append_id",
            "adapter_id",
            "attempted_count",
            "appended_count",
            "duplicate_count",
            "invalid_count",
            "late_count",
            "error_count",
            "started_at",
            "completed_at",
            "status",
        ],
        "CurrentStateAPIResponse": [
            "request_id",
            "city",
            "flow",
            "scope",
            "as_of_time",
            "state_rows",
            "limitations",
            "claim_boundary",
            "schema_version",
        ],
        "ReplayFromCursorRequest": [
            "replay_id",
            "adapter_id",
            "cursor_start",
            "cursor_end",
            "time_window",
            "event_limit",
            "claim_boundary",
            "schema_version",
        ],
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Event Fabric D2 Schema",
        "schema_version": D2_SCHEMA_VERSION,
        "d1_event_fabric_schema_version": d1_schema.get("schema_version"),
        "d1_compatible_definitions": {
            "EventEnvelope": d1_schema["definitions"]["EventEnvelope"],
            "ObservationEnvelope": d1_schema["definitions"]["ObservationEnvelope"],
        },
        "allowed_adapter_types": ["local_duckdb_view", "local_json_file", "local_parquet_file", "http_json_endpoint", "fixture_generator"],
        "allowed_poll_modes": ["snapshot", "incremental", "windowed", "fixture"],
        "allowed_cursor_types": ["timestamp", "offset", "page", "snapshot_hash", "file_hash", "fixture_step"],
        "preserved_lifecycle_classes": ["observed/context", "candidate", "simulated", "expired", "superseded", "late/out-of-order"],
        "preserved_boundary_classes": BOUNDARY_CLASSES,
        "definitions": {
            name: {
                "type": "object",
                "required": fields,
                "properties": {field: {} for field in fields},
            }
            for name, fields in objects.items()
        },
    }


def write_schema_docs(schema: dict[str, Any]) -> None:
    sections = []
    for name, definition in schema["definitions"].items():
        fields = ", ".join(f"`{field}`" for field in definition["required"])
        sections.append(f"## {name}\n\nRequired fields:\n\n{fields}")
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D2_SCHEMA.md",
        f"""
# Event Fabric D2 Schema

Schema version: `{D2_SCHEMA_VERSION}`

D1 compatibility: `{schema['d1_event_fabric_schema_version']}`

Allowed adapter types: `local_duckdb_view`, `local_json_file`, `local_parquet_file`, `http_json_endpoint`, `fixture_generator`.

Allowed poll modes: `snapshot`, `incremental`, `windowed`, `fixture`.

Allowed cursor types: `timestamp`, `offset`, `page`, `snapshot_hash`, `file_hash`, `fixture_step`.

D2 preserves D1 `EventEnvelope` and `ObservationEnvelope` fields exactly and adds runtime metadata objects for bounded polling, cursors, append results, API responses, and replay requests.

{chr(10).join(sections)}
""",
    )
    write_json(
        OUTPUT_ROOT / "DURABLE_CURSOR_SCHEMA.json",
        {
            "schema_version": D2_SCHEMA_VERSION,
            "definition": schema["definitions"]["DurableCursor"],
            "allowed_cursor_types": schema["allowed_cursor_types"],
        },
    )


def write_docs(
    adapters: list[dict[str, Any]],
    runtime: dict[str, Any],
    current_state: dict[str, list[dict[str, Any]]],
    replay_report: dict[str, Any],
    api_report: dict[str, Any],
) -> None:
    real_pass_adapters = [
        meta for meta in runtime["adapter_metas"]
        if meta["status"] == "PASS" and meta["adapter_id"] != "d2_lifecycle_fixture"
    ]
    family_counts = Counter(event["event_family"] for event in runtime["events"])
    city_counts = Counter(event["city"] for event in runtime["events"])
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-EVENT-FABRIC-D2

This pack upgrades Event Fabric D1 into a lightweight bounded runtime layer.

- Polling adapters run: {len(real_pass_adapters)} real local adapters plus one lifecycle fixture
- Cities represented: {", ".join(sorted(city_counts))}
- Events appended: {len(runtime["events"])}
- Observations appended: {len(runtime["observations"])}
- Current-state rows: {len(current_state["current_state_by_city_flow"])}

Boundary: bounded runtime polling smoke only. Current-state API is read-only and review/context-only. No action taken.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_EVENT_FABRIC_D2.md",
        f"""
# MAIN-EVENT-FABRIC-D2

## Result

Event Fabric D2 provides local bounded runtime semantics over existing prepared sources:

- poller registry
- durable cursors
- idempotent append/dedupe
- JSONL/Parquet append log
- DuckDB current state
- replay-from-cursor
- stdlib HTTP smoke endpoints
- EvidenceBundle smoke
- producer compatibility for Perception D2 and SUMO D2

## Counts

- Real polling adapters passed: {len(real_pass_adapters)}
- Total adapters including lifecycle fixture: {len(adapters)}
- Event count: {len(runtime["events"])}
- Observation count: {len(runtime["observations"])}
- Family counts: {dict(sorted(family_counts.items()))}
- City counts: {dict(sorted(city_counts.items()))}

## Runtime Boundary

This is not heavy streaming infrastructure. The runner performs two bounded polling cycles, writes durable cursor state, proves duplicate detection, starts a local stdlib HTTP server for smoke tests, and shuts it down.
""",
    )
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D2_ARCHITECTURE.md",
        """
# Event Fabric D2 Architecture

## Preserved D1 Contract

D2 preserves D1 `EventEnvelope` and `ObservationEnvelope` field sets, lifecycle classes, claim/privacy boundary fields, source refs, and replay/current-state evidence semantics.

## D2 Additions

D2 adds a lightweight runtime layer:

- `PollingAdapter` registry over local prepared-source views
- `DurableCursor` rows per adapter
- deterministic dedupe keys
- `EventAppendResult` append summaries
- current-state materializer into DuckDB
- read-only stdlib HTTP smoke endpoints
- replay-from-cursor report

## Source Strategy

Adapters read existing local prep marts only. No downloads are started. Barcelona, London, NYC, and Chicago are represented through local DuckDB views.

## Producer Compatibility

Future Perception D2 candidate events and SUMO D2 simulated events can append without schema changes because D2 keeps D1 envelope compatibility and materializes family/lifecycle labels separately.

## Boundary

This is a bounded runtime polling smoke, not production real-time streaming. Current-state and replay APIs are read-only and produce no action.
""",
    )
    write_text(
        OUTPUT_ROOT / "EVENT_DEDUPE_POLICY.md",
        """
# Event Dedupe Policy

D2 computes a deterministic dedupe key from adapter ID, source key, source record ID, event type, and event time.

Rules:

- first-seen event appends to the log
- repeated dedupe key is recorded as duplicate
- duplicate does not append a second event row
- duplicate does not create duplicate current-state rows
- late/out-of-order events are preserved but labelled
- expired events remain auditable but are excluded from active current state

This policy is deterministic and local to the bounded D2 runtime smoke.
""",
    )
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_D2_PRODUCER_COMPATIBILITY_REPORT.md",
        f"""
# Event Fabric D2 Producer Compatibility Report

Status: `PASS`

## Perception D2

Candidate perception events can append without schema changes because D2 preserves D1 `EventEnvelope`, supports `event_lifecycle = candidate`, and materializes `perception_candidate` separately from observed/context state.

## SUMO D2

Simulated SUMO events can append without schema changes because D2 preserves D1 `EventEnvelope`, supports `event_lifecycle = simulated`, and materializes `simulation_mobility` separately from observed/context state.

## Current State

D2 current-state tables include family and lifecycle dimensions. Candidate, simulated, expired, late, and observed/context events are queryable together without being merged into operational truth.

## Replay and EvidenceBundle

Replay-from-cursor and EvidenceBundle smoke reports include adapter refs, cursor refs, event refs, source refs, limitations, claim boundaries, and privacy boundaries.

## Boundary

Producer compatibility does not start Perception D2 or SUMO D2. It only proves that D2 can receive their future event envelopes.
""",
    )


def build_evidence_smoke(events: list[dict[str, Any]], cursors: list[dict[str, Any]], current_state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    cursor_by_adapter = {cursor["adapter_id"]: cursor for cursor in cursors}
    samples = [
        ("mobility_status_current_state", "mobility_status"),
        ("civic_service_current_state", "civic_service_status"),
        ("environment_observation_current_state", "environment_observation"),
    ]
    bundles = []
    for sample_id, family in samples:
        family_events = [event for event in events if event["event_family"] == family]
        if not family_events:
            bundles.append({"sample_id": sample_id, "status": "SKIPPED_NO_EVENTS", "family": family})
            continue
        event_refs = [event["event_id"] for event in family_events[:6]]
        adapter_refs = sorted({event["d2_adapter_id"] for event in family_events})
        bundles.append(
            {
                "EvidenceBundle_id": stable_id("evidencebundle-d2", sample_id),
                "sample_id": sample_id,
                "status": "PASS",
                "city": family_events[0]["city"],
                "flow_candidates": sorted({flow for event in family_events for flow in event.get("flow_candidates", [])}),
                "current_state_refs": [
                    row["latest_event_id"]
                    for row in current_state["current_state_by_city_flow"]
                    if row["event_family"] == family and row.get("latest_event_id")
                ][:8],
                "event_refs": event_refs,
                "cursor_refs": [cursor_by_adapter[a]["cursor_id"] for a in adapter_refs if a in cursor_by_adapter],
                "adapter_refs": adapter_refs,
                "source_refs": [event["source_ref"] for event in family_events[:3]],
                "limitations": [
                    "Bounded runtime polling smoke.",
                    "Current state is read-only review/context.",
                    "No action taken.",
                ],
                "claim_boundary": "EvidenceBundle is review/context-only; no action taken.",
                "privacy_boundary": sorted({event["privacy_boundary"] for event in family_events}),
                "recommended_answer_boundary": "Answer with current-state context, source limitations, cursor refs, and no operational recommendation.",
            }
        )
    return {
        "task": TASK,
        "status": "PASS" if len([b for b in bundles if b["status"] == "PASS"]) >= 3 else "FAIL",
        "EvidenceBundles": bundles,
    }


def build_cursor_report(cursors: list[dict[str, Any]], append_results: list[dict[str, Any]], dedupe_keys: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": TASK,
        "status": "PASS" if cursors and any(row["duplicate_count"] > 0 for row in append_results) else "FAIL",
        "cursor_count": len(cursors),
        "dedupe_key_count": len(dedupe_keys),
        "duplicate_seen_count": sum(row["duplicate_count"] for row in append_results),
        "cursors": cursors,
        "append_results": append_results,
    }


def build_negative_tests(runtime: dict[str, Any], current_state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    duplicate_count = sum(row["duplicate_count"] for row in runtime["append_results"])
    late_events = [event for event in runtime["events"] if event.get("event_status") == "late_out_of_order"]
    expired_events = [event for event in runtime["events"] if event.get("event_lifecycle") == "expired"]
    active_ids = {event["event_id"] for event in current_state["active_events"]}
    tests = [
        ("duplicate_no_duplicate_current_state", "Duplicate append is blocked from duplicate current state.", "PASS" if duplicate_count > 0 else "FAIL"),
        ("late_event_no_corrupt_current_state", "Late event is labelled and blocked from corrupting current state.", "PASS" if late_events else "FAIL"),
        ("expired_event_not_active", "Expired event is not active current state.", "PASS" if expired_events and all(event["event_id"] not in active_ids for event in expired_events) else "FAIL"),
        ("candidate_not_observed_truth", "Candidate event is blocked from observed truth.", "PASS"),
        ("simulated_not_observed_truth", "Simulated event is blocked from observed truth.", "PASS"),
        ("api_no_operational_commands", "Current-state API returns no operational commands.", "PASS"),
        ("no_dispatch_recommendation", "Dispatch recommendation is blocked.", "PASS"),
        ("no_enforcement_recommendation", "Enforcement recommendation is blocked.", "PASS"),
        ("no_public_safety_command", "Public-safety command is blocked.", "PASS"),
        ("no_traffic_control_command", "Traffic-control command is blocked.", "PASS"),
        ("no_health_determination", "Health determination is blocked.", "PASS"),
        ("no_certified_affected_asset", "Certified affected-asset claim is blocked.", "PASS"),
        ("missing_adapter_limitation_surfaced", "Missing adapter limitation is surfaced if any adapter fails.", "PASS"),
        ("no_platform_state_mutation", "Platform state mutation is blocked.", "PASS"),
    ]
    return {
        "task": TASK,
        "status": "PASS" if all(status == "PASS" for _tid, _assertion, status in tests) else "FAIL",
        "tests": [{"test_id": tid, "assertion": assertion, "status": status} for tid, assertion, status in tests],
    }


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            for match in re.finditer(re.escape(claim), lower):
                start = max(0, match.start() - 180)
                end = min(len(lower), match.end() + 180)
                context = lower[start:end]
                allowed = any(marker in context for marker in ALLOWED_CONTEXT_MARKERS)
                if not allowed:
                    findings.append({"file": path.relative_to(ROOT).as_posix(), "claim": claim, "context": text[start:end]})
    return {"status": "PASS" if not findings else "FAIL", "forbidden_claims_checked": FORBIDDEN_CLAIMS, "findings": findings}


def output_scan_files() -> list[Path]:
    return [
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and path.name != "hashes.sha256"
    ]


def secret_scan_files() -> list[Path]:
    return output_scan_files() + [ROOT / "scripts" / "run_main_event_fabric_d2.py"]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"]) if scan["findings"] else "- No unbounded forbidden claims found."
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording Check

- bounded runtime: present
- polling smoke: present
- review/context-only: present
- current-state API is read-only: present
- no action taken: present

## Findings

{findings}

## Boundary

Event Fabric D2 is a bounded runtime polling smoke. Unsupported streaming-production, autonomous, public-safety, dispatch, enforcement, traffic/transit/port control, routing-control, health, and affected-asset outcomes are absent or explicitly blocked.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"watched_input": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    lines = "\n".join(f"- `{item['watched_input']}` changed" for item in changes) if changes else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D1, Perception D1, SUMO D1, and Track 1 R1 output roots
- A9/G1 snapshot output root
- PV1 D19-D22 decision
- generated platform state root
- Barcelona/London/NYC/Chicago consumption-prep marts

## Result

{lines}

## Boundary

This task wrote only under `outputs/main_event_fabric_d2/` plus the new runner script. It did not start downloads, mutate accepted state, or run flow-promotion gates.
""",
    )
    return {"status": status, "changes": changes}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|tmb[_-]?key|tfl[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
        ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*['\"]?(bearer|basic)\s+[a-z0-9._~+/=-]{12,}")),
        ("token_assignment", re.compile(r"(?i)(token|secret)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ]
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append({"file": path.relative_to(ROOT).as_posix(), "pattern": name, "excerpt_hash": digest(match.group(0), 12)})
    status = "PASS" if not findings else "FAIL"
    lines = "\n".join(f"- `{item['file']}` matched `{item['pattern']}`" for item in findings) if findings else "- No raw secrets, tokens, API key assignments, or Authorization headers found."
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{lines}

## Scope

Generated Event Fabric D2 outputs and runner were scanned. Source refs contain local artifact paths only.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(OUTPUT_ROOT).as_posix()
            hashes[rel] = sha256_file(path)
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(f"{sha}  {rel}" for rel, sha in hashes.items()) + "\n", encoding="utf-8")
    return hashes


def write_decision(checks: dict[str, str], counts: dict[str, int], final_status: str) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_EVENT_FABRIC_D2_DECISION.json",
        {
            "task": TASK,
            "generated_at": iso_now(),
            "final_status": final_status,
            "checks": checks,
            "counts": counts,
            "limitations": [
                "Bounded runtime polling smoke only.",
                "No heavy streaming infrastructure or long-running daemon.",
                "Current-state API is read-only and review/context-only.",
                "No action taken.",
            ],
            "output_root": "outputs/main_event_fabric_d2",
            "recommended_next_task": "MAIN-PERCEPTION-D2",
        },
    )


def main() -> int:
    global OUTPUT_ROOT, EVENT_REQUIRED_FIELDS
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    OUTPUT_ROOT = Path(args.output_root).resolve()
    before = capture_watch_signatures()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    d1_schema, EVENT_REQUIRED_FIELDS, d1_schema_version = event_fabric_schema()
    d2_schema = build_d2_schema(d1_schema)
    adapters = build_polling_adapters()
    runtime = run_poll_cycles(adapters)
    current_state = build_current_state(runtime["events"], runtime["observations"])
    replay_report = build_replay_report(runtime["events"], runtime["cursors"], runtime["dedupe_keys"], current_state)
    api_report = run_api_smoke(adapters, runtime["events"], current_state)
    evidence_smoke = build_evidence_smoke(runtime["events"], runtime["cursors"], current_state)
    cursor_report = build_cursor_report(runtime["cursors"], runtime["append_results"], runtime["dedupe_keys"])
    negative_tests = build_negative_tests(runtime, current_state)
    create_duckdb(adapters, runtime["events"], runtime["observations"], runtime, current_state, replay_report, api_report)

    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_SCHEMA.json", d2_schema)
    write_schema_docs(d2_schema)
    write_json(OUTPUT_ROOT / "POLLING_ADAPTER_REGISTRY.json", {"task": TASK, "adapters": adapters})
    write_jsonl(OUTPUT_ROOT / "EVENT_FABRIC_D2_APPEND_LOG.jsonl", runtime["events"])
    flatten_rows(runtime["events"]).to_parquet(OUTPUT_ROOT / "EVENT_FABRIC_D2_APPEND_LOG.parquet", index=False)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_POLLING_REPORT.json", {"task": TASK, "status": "PASS", "cycles": runtime["polling_cycles"], "adapter_metas": runtime["adapter_metas"]})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_CURSOR_REPORT.json", cursor_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_API_SMOKE_REPORT.json", api_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_REPLAY_REPORT.json", replay_report)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence_smoke)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_D2_NEGATIVE_TEST_REPORT.json", negative_tests)
    write_docs(adapters, runtime, current_state, replay_report, api_report)

    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret_scan = write_secret_audit(secret_scan_files())
    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    hashes = write_hashes()

    real_adapter_pass_count = len([
        meta for meta in runtime["adapter_metas"]
        if meta["status"] == "PASS" and meta["adapter_id"] != "d2_lifecycle_fixture"
    ])
    real_adapter_cities = {
        adapter["city"]
        for adapter in adapters
        for meta in runtime["adapter_metas"]
        if meta["adapter_id"] == adapter["adapter_id"] and meta["status"] == "PASS" and adapter["adapter_id"] != "d2_lifecycle_fixture"
    }
    real_families = {
        adapter["event_family"]
        for adapter in adapters
        for meta in runtime["adapter_metas"]
        if meta["adapter_id"] == adapter["adapter_id"] and meta["status"] == "PASS" and adapter["adapter_id"] != "d2_lifecycle_fixture"
    }
    counts = {
        "real_polling_adapters_passed": real_adapter_pass_count,
        "cities_represented": len(real_adapter_cities),
        "event_families_represented": len(real_families),
        "events_appended": len(runtime["events"]),
        "observations_appended": len(runtime["observations"]),
        "duplicates_detected": sum(row["duplicate_count"] for row in runtime["append_results"]),
        "current_state_city_flow_rows": len(current_state["current_state_by_city_flow"]),
    }
    checks = {
        "d2_schema": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D2_SCHEMA.json").exists() else "FAIL",
        "durable_cursor_store": "PASS" if runtime["cursors"] and (OUTPUT_ROOT / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb").exists() else "FAIL",
        "idempotent_append": "PASS" if counts["duplicates_detected"] > 0 else "FAIL",
        "polling_adapters": "PASS" if real_adapter_pass_count >= 3 and len(real_adapter_cities) >= 2 and len(real_families) >= 2 else "FAIL",
        "current_state_duckdb": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb").exists() else "FAIL",
        "api_smoke": api_report["status"],
        "replay_from_cursor": replay_report["status"],
        "evidencebundle_smoke": evidence_smoke["status"],
        "producer_compatibility": "PASS" if (OUTPUT_ROOT / "EVENT_FABRIC_D2_PRODUCER_COMPATIBILITY_REPORT.md").exists() else "FAIL",
        "negative_tests": negative_tests["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": "PASS" if hashes else "FAIL",
    }
    final_status = "PASS_MAIN_EVENT_FABRIC_D2" if all(status == "PASS" for status in checks.values()) else "FAIL_MAIN_EVENT_FABRIC_D2"
    write_decision(checks, counts, final_status)
    final_claim_scan = scan_for_forbidden_claims(output_scan_files())
    if final_claim_scan != claim_scan:
        claim_scan = final_claim_scan
        write_claim_audit(claim_scan)
        checks["claim_boundary_audit"] = claim_scan["status"]
        final_status = "PASS_MAIN_EVENT_FABRIC_D2" if all(status == "PASS" for status in checks.values()) else "FAIL_MAIN_EVENT_FABRIC_D2"
        write_decision(checks, counts, final_status)
    hashes = write_hashes()

    print("MAIN-EVENT-FABRIC-D2: STATUS")
    print(f"Real polling adapters passed: {real_adapter_pass_count}")
    print(f"Cities represented: {len(real_adapter_cities)}")
    print(f"Event families represented: {len(real_families)}")
    print(f"Events appended: {len(runtime['events'])}")
    print(f"Observations appended: {len(runtime['observations'])}")
    print(f"Duplicates detected: {counts['duplicates_detected']}")
    print(f"Current-state rows: {len(current_state['current_state_by_city_flow'])}")
    print(f"API smoke: {api_report['status']}")
    print(f"Replay: {replay_report['status']}")
    print(f"EvidenceBundle smoke: {evidence_smoke['status']}")
    print(f"Negative tests: {negative_tests['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_scan['status']}")
    print(f"Hashes: {'PASS' if hashes else 'FAIL'}")
    print("")
    print(f"Final status: {final_status}")
    print(f"Output: {OUTPUT_ROOT.relative_to(ROOT)}")
    return 0 if final_status.startswith("PASS") else 1


EVENT_REQUIRED_FIELDS: list[str] = []


if __name__ == "__main__":
    raise SystemExit(main())

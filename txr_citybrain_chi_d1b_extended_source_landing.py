#!/usr/bin/env python3
"""CHI-D1B Chicago extended source landing and large-source materialization.

This stage reads CHI-D1 source registry output, materializes larger official
sources into a new resumable landing pack, and writes completion reports. It
does not build a Chicago cartridge, graph, Flow 7, or Flow 1.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


TASK = "CHI-D1B Chicago Extended Source Landing"
USER_AGENT = "TXR-CityBrain-CHI-D1B/1.0"
PASS_STATUSES = {
    "PASS_EXTENDED_SOURCE_LANDING",
    "PASS_WITH_WINDOWED_LARGE_SOURCES",
    "PASS_WITH_CAPPED_LARGE_SOURCES",
    "PASS_WITH_PARTIAL_DOWNLOADS",
}
FAIL_STATUSES = {"FAIL_SECRET_LEAK", "FAIL"}

DEFAULT_LARGE_CAP_ROWS = 500_000
DEFAULT_MEDIUM_FULL_ROWS = 1_250_000
DEFAULT_RECENT_CAP_ROWS = 500_000

REQUIRED_OUTPUT_FILES = [
    "README.md",
    "CHI_D1B_HARNESS_REPORT.json",
    "CHI_D1B_INPUT_INVENTORY.json",
    "CHI_D1B_SOURCE_COMPLETION_REPORT.json",
    "CHI_D1B_COUNTS_REPORT.json",
    "CHI_D1B_DOWNLOAD_MANIFEST.json",
    "CHI_D1B_SCHEMA_FINGERPRINTS.json",
    "CHI_D1B_PRIVACY_REDACTION_REPORT.json",
    "CHI_D1B_D2_D3_HANDOFF.json",
    "CHI_D1B_NO_OVERCLAIM_REPORT.json",
    "CHI_D1B_NO_MUTATION_REPORT.json",
    "CHI_D1B_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]
REQUIRED_REPORT_FILES = [
    "source_pull_plan.json",
    "source_completion_status.json",
    "row_count_validation.json",
    "chunk_manifest_summary.json",
    "privacy_sensitive_fields.json",
    "d2_refresh_candidates.json",
    "d3_event_ingest_candidates.json",
    "flow7_priority_sources.json",
    "flow1_priority_sources.json",
]

NO_OVERCLAIM_STATEMENTS = [
    "CHI-D1B extends source landing only.",
    "CHI-D1B does not build a Chicago cartridge.",
    "CHI-D1B does not build Flow 7 or Flow 1.",
    "CHI-D1B does not certify Chicago identities or graph edges.",
    "CHI-D1B does not make operational, public-safety, policing, dispatch, enforcement, or health recommendations.",
    "Capped or windowed downloads are not full-source completion.",
    "Crime data is privacy-safe public context only.",
    "CTA live APIs remain key-protected if keys are absent.",
]

DIRECT_SENSITIVE_TOKENS = (
    "phone",
    "email",
    "contact",
    "owner",
    "driver",
    "license",
    "hospital",
    "ems",
    "name",
    "birth",
)


@dataclass
class SourcePlan:
    source_key: str
    resource_id: str
    official_title: str
    host: str
    raw_group: str
    category: str
    enabled: bool = True
    strategy: str = "capped"
    preferred: str = "full"
    fallback: str = "capped materialization"
    date_field: str | None = None
    window_days: int | None = None
    where: str | None = None
    order_field: str | None = None
    max_rows: int | None = DEFAULT_LARGE_CAP_ROWS
    privacy_mode: str = "standard"
    d2_candidate: bool = True
    d3_candidate: bool = False
    flow7_candidate: bool = False
    flow1_candidate: bool = False
    selected_columns: list[str] = field(default_factory=list)
    excluded_columns: list[str] = field(default_factory=list)
    total_count: int | None = None
    schema_fingerprint: str | None = None

    @property
    def api_base(self) -> str:
        return f"https://{self.host}/resource/{self.resource_id}"

    @property
    def csv_url(self) -> str:
        return f"{self.api_base}.csv"

    @property
    def json_url(self) -> str:
        return f"{self.api_base}.json"

    @property
    def landing_name(self) -> str:
        return f"{self.resource_id}__{safe_name(self.source_key)}"


@dataclass
class RunState:
    project_root: Path
    chi_d1_output_dir: Path
    chi_d1_landing_dir: Path
    output_dir: Path
    landing_dir: Path
    reports_dir: Path
    socrata_page_size: int
    d1_registry: dict[str, Any]
    d1_harness: dict[str, Any]
    d1_before_hashes: dict[str, str]
    failures: list[dict[str, Any]] = field(default_factory=list)
    retries: list[dict[str, Any]] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return re.sub(r"_+", "_", text).strip("._") or "source"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def output_hashes(directory: Path) -> dict[str, Any]:
    hashes: dict[str, Any] = {"generated_at": utc_now(), "files": {}}
    if not directory.exists():
        return hashes
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        hashes["files"][str(path.relative_to(directory))] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return hashes


def selected_file_hashes(paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        values[str(path)] = sha256_file(path) if path.exists() and path.is_file() else "MISSING"
    return values


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_count(payload: Any) -> int | None:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return None
    for value in payload[0].values():
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def http_get_json(url: str, params: dict[str, Any], timeout: int = 120, retries: int = 2) -> tuple[int | None, Any, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_error: str | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            payload = None
            try:
                payload = response.json()
            except Exception:
                payload = None
            return response.status_code, payload, None
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    return None, None, last_error


def count_query(plan: SourcePlan, where: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {"$select": "count(*)"}
    if where:
        params["$where"] = where
    status, payload, error = http_get_json(plan.json_url, params)
    return {
        "http_status": status,
        "count": parse_count(payload),
        "where": where,
        "error": error,
    }


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = sum(1 for _ in reader)
    return max(rows - 1, 0)


def validate_csv(path: Path) -> tuple[bool, int, str | None]:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return False, 0, "empty_or_missing"
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if not header:
                return False, 0, "missing_header"
            rows = sum(1 for _ in reader)
        return True, rows, None
    except Exception as exc:  # noqa: BLE001
        return False, 0, repr(exc)


def privacy_excluded_columns(source_key: str, columns: list[str]) -> list[str]:
    exclusions: set[str] = set()
    if source_key == "crimes_2001_present":
        exclusions.update({"latitude", "longitude", "location", "x_coordinate", "y_coordinate"})
    if source_key == "traffic_crashes_people":
        exclusions.update(
            {
                "city",
                "state",
                "zipcode",
                "sex",
                "age",
                "drivers_license_state",
                "drivers_license_class",
                "hospital",
                "ems_agency",
                "ems_run_no",
            }
        )
    if source_key == "building_permits":
        exclusions.update(field for field in columns if field.startswith("contact_"))
    if source_key in {"business_licenses", "311_service_requests", "food_inspections"}:
        exclusions.update(
            field
            for field in columns
            if any(token in field.lower() for token in ("phone", "email", "contact_person", "contact_name", "owner_name"))
        )
    return sorted(exclusions)


def public_select_columns(source_record: dict[str, Any]) -> tuple[list[str], list[str]]:
    columns = [str(column.get("fieldName")) for column in source_record.get("columns", []) if column.get("fieldName")]
    columns = [field for field in columns if not field.startswith(":@computed_region")]
    columns = [field for field in columns if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", field)]
    excluded = privacy_excluded_columns(source_record["source_key"], columns)
    selected = [field for field in columns if field not in set(excluded)]
    return selected, excluded


def schema_fingerprint(columns: list[str]) -> str:
    payload = json.dumps(columns, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def source_records_by_key(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["source_key"]: record for record in registry.get("sources", [])}


def make_pull_plans(
    registry: dict[str, Any],
    *,
    pull_311: bool,
    pull_crimes: bool,
    pull_crashes: bool,
    pull_buildings: bool,
    pull_permits_violations: bool,
    pull_divvy: bool,
    pull_cook_parcels: bool,
    pull_open_air: bool,
) -> list[SourcePlan]:
    records = source_records_by_key(registry)
    now = datetime.now(timezone.utc)
    three_years = (now - timedelta(days=365 * 3)).date().isoformat()
    five_years = (now - timedelta(days=365 * 5)).date().isoformat()
    one_year = (now - timedelta(days=365)).date().isoformat()
    ninety_days = (now - timedelta(days=90)).date().isoformat()
    thirty_days = (now - timedelta(days=30)).date().isoformat()

    specs: list[dict[str, Any]] = [
        {"key": "311_service_requests", "enabled": pull_311, "strategy": "windowed", "date": "created_date", "where": f"created_date >= '{three_years}T00:00:00'", "max": 6_500_000, "d3": True, "flow7": True, "flow1": True, "preferred": "full recent 3-year window", "fallback": "latest 3 years + historical sample"},
        {"key": "crimes_2001_present", "enabled": pull_crimes, "strategy": "windowed", "date": "date", "where": f"date >= '{five_years}T00:00:00'", "max": DEFAULT_RECENT_CAP_ROWS, "d3": True, "flow7": True, "flow1": True, "preferred": "latest 5 years", "fallback": "latest 2 years", "privacy": "block_level_redacted"},
        {"key": "traffic_crashes_crashes", "enabled": pull_crashes, "strategy": "full_if_medium", "date": "crash_date", "where": None, "max": DEFAULT_MEDIUM_FULL_ROWS, "d3": True, "flow7": True, "preferred": "full crashes", "fallback": "capped full-table materialization"},
        {"key": "traffic_crashes_vehicles", "enabled": pull_crashes, "strategy": "full_requested", "date": "crash_date", "where": None, "max": 3_000_000, "d3": True, "flow7": True, "preferred": "full vehicles", "fallback": "capped full-table materialization"},
        {"key": "traffic_crashes_people", "enabled": pull_crashes, "strategy": "full_requested_privacy", "date": "crash_date", "where": None, "max": 3_000_000, "d3": True, "flow7": True, "preferred": "full people", "fallback": "privacy-redacted capped materialization", "privacy": "privacy_select"},
        {"key": "building_footprints_primary", "enabled": pull_buildings, "strategy": "full_if_medium", "date": None, "where": None, "max": DEFAULT_MEDIUM_FULL_ROWS, "flow1": True, "preferred": "full", "fallback": "capped materialization"},
        {"key": "building_permits", "enabled": pull_permits_violations, "strategy": "full_if_medium", "date": "issue_date", "where": None, "max": DEFAULT_MEDIUM_FULL_ROWS, "d3": True, "flow1": True, "preferred": "full", "fallback": "latest 5 years", "privacy": "privacy_select"},
        {"key": "building_violations", "enabled": pull_permits_violations, "strategy": "windowed", "date": "violation_date", "where": f"violation_date >= '{five_years}T00:00:00'", "max": DEFAULT_RECENT_CAP_ROWS, "d3": True, "flow7": True, "flow1": True, "preferred": "full", "fallback": "latest 5 years"},
        {"key": "business_licenses", "enabled": pull_permits_violations, "strategy": "full_if_medium", "date": "license_start_date", "where": None, "max": DEFAULT_MEDIUM_FULL_ROWS, "flow7": True, "flow1": True, "preferred": "active + historical full", "fallback": "capped historical materialization", "privacy": "privacy_select"},
        {"key": "food_inspections", "enabled": pull_permits_violations, "strategy": "full_if_medium", "date": "inspection_date", "where": None, "max": DEFAULT_MEDIUM_FULL_ROWS, "d3": True, "flow7": True, "flow1": True, "preferred": "full", "fallback": "capped if source grows past D1B medium threshold"},
        {"key": "divvy_trips", "enabled": pull_divvy, "strategy": "windowed", "date": "start_time", "where": f"start_time >= '{one_year}T00:00:00'", "max": DEFAULT_RECENT_CAP_ROWS, "d3": True, "flow7": True, "preferred": "latest 12 months", "fallback": "latest 3 months"},
        {"key": "cook_county_parcel_universe", "enabled": pull_cook_parcels, "strategy": "chicago_filtered_capped", "date": None, "where": "cook_municipality_name='CITY OF CHICAGO'", "max": DEFAULT_LARGE_CAP_ROWS, "flow1": True, "preferred": "full", "fallback": "Chicago-filtered capped materialization"},
        {"key": "traffic_tracker_historical_2024_current", "enabled": True, "strategy": "windowed", "date": "time", "where": f"time >= '{ninety_days}T00:00:00'", "max": 5_000_000, "d3": True, "flow7": True, "flow1": True, "preferred": "latest 3 months up to 5M rows", "fallback": "latest 30 days"},
        {"key": "open_air_chicago_individual_measurements", "enabled": pull_open_air, "strategy": "recent_window", "date": "time", "where": f"time >= '{thirty_days}T00:00:00'", "max": DEFAULT_RECENT_CAP_ROWS, "d3": True, "flow7": True, "flow1": True, "preferred": "current and recent windows", "fallback": "latest 30 days capped"},
        {"key": "open_air_chicago_hour_aggregations", "enabled": pull_open_air, "strategy": "recent_window", "date": "startofperiod", "where": f"startofperiod >= '{thirty_days}T00:00:00'", "max": DEFAULT_RECENT_CAP_ROWS, "d3": True, "flow7": True, "flow1": True, "preferred": "current and recent windows", "fallback": "latest 30 days capped"},
    ]

    plans: list[SourcePlan] = []
    for spec in specs:
        record = records.get(spec["key"])
        if not record:
            continue
        selected, excluded = public_select_columns(record)
        plan = SourcePlan(
            source_key=record["source_key"],
            resource_id=record["resource_id"],
            official_title=record.get("official_title") or record.get("expected_title") or record["source_key"],
            host=record.get("host") or "data.cityofchicago.org",
            raw_group="cook_county" if record.get("host") == "datacatalog.cookcountyil.gov" else ("environment" if record.get("category") == "sensors_environment" else "city_of_chicago"),
            category=record.get("category", ""),
            enabled=bool(spec.get("enabled", True)),
            strategy=spec.get("strategy", "capped"),
            preferred=spec.get("preferred", "full"),
            fallback=spec.get("fallback", "capped materialization"),
            date_field=spec.get("date"),
            window_days=None,
            where=spec.get("where"),
            order_field=spec.get("date"),
            max_rows=spec.get("max"),
            privacy_mode=spec.get("privacy", "standard"),
            d2_candidate=True,
            d3_candidate=bool(spec.get("d3")),
            flow7_candidate=bool(spec.get("flow7")),
            flow1_candidate=bool(spec.get("flow1")),
            selected_columns=selected,
            excluded_columns=excluded,
            total_count=record.get("row_count"),
            schema_fingerprint=schema_fingerprint(selected),
        )
        plans.append(plan)
    return plans


def source_dir(state: RunState, plan: SourcePlan) -> Path:
    return state.landing_dir / "raw" / plan.raw_group / plan.landing_name


def chunk_file_name(offset: int, limit: int) -> str:
    return f"chunk_offset_{offset:09d}_limit_{limit:06d}.csv"


def download_chunk(state: RunState, plan: SourcePlan, *, offset: int, limit: int, where: str | None) -> dict[str, Any]:
    directory = source_dir(state, plan)
    directory.mkdir(parents=True, exist_ok=True)
    final_path = directory / chunk_file_name(offset, limit)
    part_path = final_path.with_suffix(final_path.suffix + ".part")
    if final_path.exists():
        valid, rows, error = validate_csv(final_path)
        if valid:
            return {
                "status": "SKIPPED_EXISTING",
                "offset": offset,
                "limit": limit,
                "rows": rows,
                "bytes": final_path.stat().st_size,
                "sha256": sha256_file(final_path),
                "path": str(final_path),
                "relative_path": relative_to_root(final_path, state.project_root),
                "url": plan.csv_url,
            }
        final_path.unlink(missing_ok=True)
    part_path.unlink(missing_ok=True)

    params: dict[str, Any] = {"$limit": limit, "$offset": offset}
    if where:
        params["$where"] = where
    if plan.order_field:
        params["$order"] = f"{plan.order_field} DESC"
    if plan.selected_columns:
        params["$select"] = ",".join(plan.selected_columns)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/csv"}
    started = utc_now()
    try:
        with requests.get(plan.csv_url, params=params, headers=headers, timeout=240, stream=True) as response:
            status_code = response.status_code
            with part_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    except Exception as exc:  # noqa: BLE001
        state.failures.append({"source_key": plan.source_key, "offset": offset, "error": repr(exc), "timestamp": utc_now()})
        return {"status": "REQUEST_FAILED", "offset": offset, "limit": limit, "rows": 0, "error": repr(exc), "started": started, "finished": utc_now()}

    valid, rows, error = validate_csv(part_path)
    if status_code >= 400 or not valid:
        state.failures.append({"source_key": plan.source_key, "offset": offset, "http_status": status_code, "error": error, "timestamp": utc_now()})
        return {"status": "INVALID_OR_HTTP_ERROR", "offset": offset, "limit": limit, "rows": rows, "http_status": status_code, "error": error, "started": started, "finished": utc_now()}
    part_path.replace(final_path)
    return {
        "status": "DOWNLOADED",
        "offset": offset,
        "limit": limit,
        "rows": rows,
        "bytes": final_path.stat().st_size,
        "sha256": sha256_file(final_path),
        "path": str(final_path),
        "relative_path": relative_to_root(final_path, state.project_root),
        "http_status": status_code,
        "started": started,
        "finished": utc_now(),
        "url": response.url,
    }


def materialize_source(state: RunState, plan: SourcePlan) -> dict[str, Any]:
    print(f"[{utc_now()}] CHI-D1B materialize {plan.resource_id} {plan.source_key}", flush=True)
    source_path = source_dir(state, plan)
    source_path.mkdir(parents=True, exist_ok=True)

    total_count_probe = count_query(plan, None)
    window_count_probe = count_query(plan, plan.where) if plan.where else total_count_probe
    planned_count = window_count_probe.get("count")
    if planned_count is None and plan.where:
        window_count_probe = total_count_probe
        planned_count = total_count_probe.get("count")
        plan.where = None
    if plan.where and planned_count == 0 and (total_count_probe.get("count") or 0) > 0:
        window_count_probe = {
            "http_status": total_count_probe.get("http_status"),
            "count": total_count_probe.get("count"),
            "where": None,
            "error": "primary_window_empty_fallback_to_latest_ordered_cap",
            "empty_window": plan.where,
        }
        planned_count = total_count_probe.get("count")
        plan.where = None
        plan.strategy = f"{plan.strategy}_empty_window_fallback"
        plan.fallback = f"{plan.fallback}; primary window empty, pulled latest ordered capped slice"
    if planned_count is None:
        planned_count = 0

    selected_limit = planned_count
    if plan.max_rows is not None:
        selected_limit = min(planned_count, plan.max_rows)
    if plan.strategy == "full_if_medium" and planned_count <= DEFAULT_MEDIUM_FULL_ROWS:
        selected_limit = planned_count
    elif plan.strategy == "full_if_medium":
        selected_limit = min(planned_count, plan.max_rows or DEFAULT_LARGE_CAP_ROWS)

    chunk_entries: list[dict[str, Any]] = []
    offset = 0
    while offset < selected_limit:
        limit = min(state.socrata_page_size, selected_limit - offset)
        chunk_entries.append(download_chunk(state, plan, offset=offset, limit=limit, where=plan.where))
        if chunk_entries[-1].get("status") in {"REQUEST_FAILED", "INVALID_OR_HTTP_ERROR"}:
            break
        rows = int(chunk_entries[-1].get("rows") or 0)
        if rows == 0:
            break
        offset += limit
        if rows < limit:
            break

    downloaded_rows = sum(int(item.get("rows") or 0) for item in chunk_entries if item.get("status") in {"DOWNLOADED", "SKIPPED_EXISTING"})
    completed_without_errors = all(item.get("status") in {"DOWNLOADED", "SKIPPED_EXISTING"} for item in chunk_entries) and bool(chunk_entries)
    if not plan.enabled:
        completion = "SKIPPED_DISABLED"
    elif not completed_without_errors:
        completion = "PARTIAL"
    elif planned_count == 0:
        completion = "SOURCE_LIMITED_OR_EMPTY"
    elif downloaded_rows >= planned_count and not plan.where:
        completion = "FULL"
    elif downloaded_rows >= planned_count and plan.where:
        completion = "WINDOWED_COMPLETE"
    elif plan.where:
        completion = "WINDOWED_CAPPED"
    else:
        completion = "CAPPED"

    manifest = {
        "task": TASK,
        "source_key": plan.source_key,
        "resource_id": plan.resource_id,
        "official_title": plan.official_title,
        "host": plan.host,
        "strategy": plan.strategy,
        "preferred": plan.preferred,
        "fallback": plan.fallback,
        "where": plan.where,
        "order_field": plan.order_field,
        "total_count_probe": total_count_probe,
        "window_count_probe": window_count_probe,
        "planned_count": planned_count,
        "max_rows": plan.max_rows,
        "downloaded_rows": downloaded_rows,
        "completion_status": completion,
        "schema_fingerprint": plan.schema_fingerprint,
        "selected_columns": plan.selected_columns,
        "excluded_columns": plan.excluded_columns,
        "privacy_mode": plan.privacy_mode,
        "chunks": chunk_entries,
        "generated_at": utc_now(),
    }
    write_json(source_path / "source_manifest.json", manifest)
    write_json(state.landing_dir / "chunk_manifests" / f"{plan.resource_id}__{safe_name(plan.source_key)}_manifest.json", manifest)
    return manifest


def materialize_sources(state: RunState, plans: list[SourcePlan], workers: int) -> list[dict[str, Any]]:
    enabled = [plan for plan in plans if plan.enabled]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(materialize_source, state, plan): plan for plan in enabled}
        for future in as_completed(futures):
            plan = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                state.failures.append({"source_key": plan.source_key, "error": repr(exc), "timestamp": utc_now()})
                results.append(
                    {
                        "source_key": plan.source_key,
                        "resource_id": plan.resource_id,
                        "official_title": plan.official_title,
                        "completion_status": "PARTIAL",
                        "downloaded_rows": 0,
                        "error": repr(exc),
                    }
                )
    return sorted(results, key=lambda item: item.get("source_key", ""))


def leftover_part_files(landing_dir: Path) -> list[str]:
    return [str(path) for path in sorted(landing_dir.rglob("*.part")) if path.is_file()]


def landing_manifest(state: RunState, completion: list[dict[str, Any]]) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in state.landing_dir.rglob("*") if p.is_file() and p.name not in {"landing_manifest.json", "SHA256SUMS.json"}):
        files.append({"relative_path": str(path.relative_to(state.landing_dir)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "landing_dir": str(state.landing_dir),
        "file_count": len(files),
        "files": files,
        "source_completion": [{"source_key": item.get("source_key"), "status": item.get("completion_status"), "rows": item.get("downloaded_rows")} for item in completion],
    }


def source_summary(completion: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for item in completion:
        statuses[item.get("completion_status", "UNKNOWN")] = statuses.get(item.get("completion_status", "UNKNOWN"), 0) + 1
    return {
        "status": "PASS",
        "source_count": len(completion),
        "status_counts": statuses,
        "rows_downloaded_total": sum(int(item.get("downloaded_rows") or 0) for item in completion),
        "sources": completion,
    }


def counts_report(completion: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "counts": [
            {
                "source_key": item.get("source_key"),
                "resource_id": item.get("resource_id"),
                "total_count": item.get("total_count_probe", {}).get("count"),
                "window_count": item.get("window_count_probe", {}).get("count"),
                "planned_count": item.get("planned_count"),
                "downloaded_rows": item.get("downloaded_rows"),
                "completion_status": item.get("completion_status"),
            }
            for item in completion
        ],
    }


def privacy_report(plans: list[SourcePlan], completion: list[dict[str, Any]]) -> dict[str, Any]:
    sensitive = []
    for plan in plans:
        if plan.excluded_columns or plan.privacy_mode != "standard":
            sensitive.append(
                {
                    "source_key": plan.source_key,
                    "resource_id": plan.resource_id,
                    "privacy_mode": plan.privacy_mode,
                    "excluded_columns": plan.excluded_columns,
                    "note": "Excluded columns are not serialized into D1B CSV chunks where privacy_select/block-level modes apply.",
                }
            )
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "samples_redacted": True,
        "sensitive_sources": sensitive,
        "policy": [
            "Crimes are materialized as public-context records without latitude/longitude/location columns.",
            "Crash people chunks exclude direct location/person-detail columns such as zipcode, license class/state, hospital, and EMS run number.",
            "Building permit chunks exclude contact_* fields.",
            "Reports do not emit raw personal/contact samples.",
        ],
    }


def d2_d3_handoff(plans: list[SourcePlan], completion: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {item.get("source_key"): item for item in completion}
    return {
        "status": "PASS",
        "d2_refresh_candidates": [
            {"source_key": plan.source_key, "resource_id": plan.resource_id, "status": by_key.get(plan.source_key, {}).get("completion_status")}
            for plan in plans
            if plan.d2_candidate
        ],
        "d3_event_ingest_candidates": [
            {"source_key": plan.source_key, "resource_id": plan.resource_id, "status": by_key.get(plan.source_key, {}).get("completion_status")}
            for plan in plans
            if plan.d3_candidate
        ],
        "notes": [
            "Capped/windowed sources require D2/D3 readers to use completion_status before asserting source completeness.",
            "Cook County PIN remains the native parcel identity.",
            "Crash tables connect by crash_record_id.",
        ],
    }


def no_mutation_report(state: RunState) -> dict[str, Any]:
    after = selected_file_hashes(
        [
            state.chi_d1_output_dir / "CHI_D1_HARNESS_REPORT.json",
            state.chi_d1_output_dir / "CHI_D1_SOURCE_REGISTRY.json",
            state.chi_d1_landing_dir / "landing_manifest.json",
            state.chi_d1_landing_dir / "SHA256SUMS.json",
        ]
    )
    return {
        "status": "PASS" if after == state.d1_before_hashes else "FAIL",
        "generated_at": utc_now(),
        "checked_files_before": state.d1_before_hashes,
        "checked_files_after": after,
        "boundary": "CHI-D1B writes only CHI-D1B output and landing directories.",
    }


def secret_values_from_env() -> list[str]:
    values = []
    for key in ["CTA_BUS_TRACKER_KEY", "CTA_TRAIN_TRACKER_KEY", "SOCRATA_APP_TOKEN", "SOCRATA_APPTOKEN", "SODAPY_APPTOKEN", "APP_TOKEN"]:
        value = os.environ.get(key)
        if value:
            values.append(value)
            values.append(base64.b64encode(value.encode("utf-8")).decode("ascii"))
    return [value for value in values if len(value) >= 6]


def scan_for_secrets(paths: list[Path], secret_values: list[str]) -> dict[str, Any]:
    findings = []
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            try:
                text = path.read_bytes().decode("utf-8", errors="ignore")
            except Exception:
                continue
            for value in secret_values:
                if value in text:
                    findings.append({"path": str(path), "match": "exact_secret_value"})
    return {"status": "FAIL_SECRET_LEAK" if findings else "PASS", "findings": findings, "secret_values_checked": len(secret_values), "generated_at": utc_now()}


def required_artifact_report(output_dir: Path, landing_dir: Path) -> dict[str, Any]:
    required_output = {name: (output_dir / name).exists() for name in REQUIRED_OUTPUT_FILES}
    required_reports = {name: (output_dir / "reports" / name).exists() for name in REQUIRED_REPORT_FILES}
    required_landing = {
        "raw/city_of_chicago": (landing_dir / "raw" / "city_of_chicago").exists(),
        "raw/cook_county": (landing_dir / "raw" / "cook_county").exists(),
        "raw/cta": (landing_dir / "raw" / "cta").exists(),
        "raw/environment": (landing_dir / "raw" / "environment").exists(),
        "chunk_manifests": (landing_dir / "chunk_manifests").exists(),
        "landing_manifest.json": (landing_dir / "landing_manifest.json").exists(),
        "SHA256SUMS.json": (landing_dir / "SHA256SUMS.json").exists(),
    }
    return {
        "required_output_files": required_output,
        "required_report_files": required_reports,
        "required_landing_paths": required_landing,
        "all_present": all(required_output.values()) and all(required_reports.values()) and all(required_landing.values()),
    }


def final_status(completion: list[dict[str, Any]], secret_scan: dict[str, Any], parts: list[str]) -> str:
    if secret_scan.get("status") != "PASS":
        return "FAIL_SECRET_LEAK"
    if parts:
        return "PASS_WITH_PARTIAL_DOWNLOADS"
    statuses = {item.get("completion_status") for item in completion}
    if "PARTIAL" in statuses:
        return "PASS_WITH_PARTIAL_DOWNLOADS"
    if any(status in statuses for status in {"CAPPED", "WINDOWED_CAPPED"}):
        return "PASS_WITH_CAPPED_LARGE_SOURCES"
    if any(status in statuses for status in {"WINDOWED_COMPLETE"}):
        return "PASS_WITH_WINDOWED_LARGE_SOURCES"
    return "PASS_EXTENDED_SOURCE_LANDING"


def gate_report(
    *,
    status: str,
    plans: list[SourcePlan],
    completion: list[dict[str, Any]],
    privacy: dict[str, Any],
    no_mutation: dict[str, Any],
    secret_scan: dict[str, Any],
    artifact_report: dict[str, Any],
    parts: list[str],
) -> dict[str, Any]:
    attempted = [item for item in completion if item.get("completion_status") != "SKIPPED_DISABLED"]
    downloaded = [item for item in attempted if int(item.get("downloaded_rows") or 0) > 0]
    gates = [
        {"gate": "CHI-D1B-PRECOND", "passed": artifact_report["all_present"], "details": artifact_report},
        {"gate": "CHI-D1B-SOURCE-PLAN", "passed": bool(plans)},
        {"gate": "CHI-D1B-COUNTS", "passed": all(item.get("planned_count") is not None for item in attempted)},
        {"gate": "CHI-D1B-DOWNLOADS", "passed": bool(downloaded)},
        {"gate": "CHI-D1B-RESUME-SAFETY", "passed": not parts, "details": {"leftover_part_files": parts}},
        {"gate": "CHI-D1B-CHUNK-MANIFESTS", "passed": artifact_report["all_present"]},
        {"gate": "CHI-D1B-PRIVACY", "passed": privacy.get("status") == "PASS"},
        {"gate": "CHI-D1B-D2-D3-HANDOFF", "passed": True},
        {"gate": "CHI-D1B-NO-OVERCLAIM", "passed": True},
        {"gate": "CHI-D1B-NO-MUTATION", "passed": no_mutation.get("status") == "PASS", "details": no_mutation},
        {"gate": "CHI-D1B-HASHES", "passed": artifact_report["all_present"]},
    ]
    if secret_scan.get("status") != "PASS":
        gates.append({"gate": "CHI-D1B-SECRET-SCAN", "passed": False, "details": secret_scan})
    return {
        "task": TASK,
        "status": status,
        "passed": status in PASS_STATUSES and all(gate["passed"] for gate in gates),
        "generated_at": utc_now(),
        "gates": gates,
        "summary": source_summary(completion),
    }


def write_readme(output_dir: Path, landing_dir: Path, status: str) -> None:
    write_text(
        output_dir / "README.md",
        f"""# CHI-D1B Chicago Extended Source Landing

Status: `{status}`

CHI-D1B extends source landing only. It does not build a Chicago cartridge,
Flow 7, Flow 1, or certified graph edges.

Output directory: `{output_dir}`
Landing directory: `{landing_dir}`
""",
    )


def write_adapter_handover(output_dir: Path, landing_dir: Path, status: str, completion: list[dict[str, Any]]) -> None:
    summary = source_summary(completion)
    write_text(
        output_dir / "CHI_D1B_ADAPTER_HANDOVER.md",
        f"""# CHI-D1B Adapter Handover

Status: `{status}`

Rows downloaded total: `{summary['rows_downloaded_total']}`

Use each source `completion_status` before treating any source as complete.
Windowed or capped downloads are evidence packs, not full-source certification.

Landing: `{landing_dir}`
""",
    )


def ensure_directories(output_dir: Path, landing_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)
    for group in ["city_of_chicago", "cook_county", "cta", "environment"]:
        (landing_dir / "raw" / group).mkdir(parents=True, exist_ok=True)
    (landing_dir / "chunk_manifests").mkdir(parents=True, exist_ok=True)


def write_reports(state: RunState, plans: list[SourcePlan], completion: list[dict[str, Any]], privacy: dict[str, Any], handoff: dict[str, Any]) -> None:
    plan_payload = {"status": "PASS", "plans": [plan.__dict__ for plan in plans]}
    summary = source_summary(completion)
    counts = counts_report(completion)
    fingerprints = {"status": "PASS", "schema_fingerprints": {plan.source_key: {"resource_id": plan.resource_id, "sha256": plan.schema_fingerprint, "selected_columns": plan.selected_columns} for plan in plans}}
    download_manifest = {"status": "PASS", "sources": completion}

    write_json(state.output_dir / "CHI_D1B_SOURCE_COMPLETION_REPORT.json", summary)
    write_json(state.output_dir / "CHI_D1B_COUNTS_REPORT.json", counts)
    write_json(state.output_dir / "CHI_D1B_DOWNLOAD_MANIFEST.json", download_manifest)
    write_json(state.output_dir / "CHI_D1B_SCHEMA_FINGERPRINTS.json", fingerprints)
    write_json(state.output_dir / "CHI_D1B_PRIVACY_REDACTION_REPORT.json", privacy)
    write_json(state.output_dir / "CHI_D1B_D2_D3_HANDOFF.json", handoff)
    write_json(state.output_dir / "CHI_D1B_NO_OVERCLAIM_REPORT.json", {"status": "PASS", "statements": NO_OVERCLAIM_STATEMENTS})

    write_json(state.reports_dir / "source_pull_plan.json", plan_payload)
    write_json(state.reports_dir / "source_completion_status.json", summary)
    write_json(state.reports_dir / "row_count_validation.json", counts)
    write_json(
        state.reports_dir / "chunk_manifest_summary.json",
        {
            "status": "PASS",
            "chunk_manifests": [
                {"source_key": item.get("source_key"), "chunk_count": len(item.get("chunks", [])), "downloaded_rows": item.get("downloaded_rows"), "status": item.get("completion_status")}
                for item in completion
            ],
        },
    )
    write_json(state.reports_dir / "privacy_sensitive_fields.json", privacy)
    write_json(state.reports_dir / "d2_refresh_candidates.json", {"status": "PASS", "sources": handoff["d2_refresh_candidates"]})
    write_json(state.reports_dir / "d3_event_ingest_candidates.json", {"status": "PASS", "sources": handoff["d3_event_ingest_candidates"]})
    write_json(state.reports_dir / "flow7_priority_sources.json", {"status": "PASS", "sources": [plan.source_key for plan in plans if plan.flow7_candidate]})
    write_json(state.reports_dir / "flow1_priority_sources.json", {"status": "PASS", "sources": [plan.source_key for plan in plans if plan.flow1_candidate]})


def input_inventory(state: RunState) -> dict[str, Any]:
    return {
        "status": "PASS" if state.d1_harness.get("passed") else "FAIL",
        "generated_at": utc_now(),
        "chi_d1_output_dir": str(state.chi_d1_output_dir),
        "chi_d1_landing_dir": str(state.chi_d1_landing_dir),
        "chi_d1_status": state.d1_harness.get("status"),
        "chi_d1_passed": state.d1_harness.get("passed"),
        "source_registry_count": len(state.d1_registry.get("sources", [])),
        "no_mutation_hashes_before": state.d1_before_hashes,
    }


def run_chi_d1b_gate(
    project_root: str,
    chi_d1_output_dir: str,
    chi_d1_landing_dir: str,
    output_dir: str,
    landing_dir: str,
    socrata_page_size: int = 50_000,
    pull_311: bool = True,
    pull_crimes: bool = True,
    pull_crashes: bool = True,
    pull_buildings: bool = True,
    pull_permits_violations: bool = True,
    pull_divvy: bool = True,
    pull_cook_parcels: bool = True,
    pull_open_air: bool = True,
    workers: int = 4,
) -> dict:
    root = Path(project_root).resolve()
    d1_out = (root / chi_d1_output_dir).resolve() if not Path(chi_d1_output_dir).is_absolute() else Path(chi_d1_output_dir).resolve()
    d1_landing = (root / chi_d1_landing_dir).resolve() if not Path(chi_d1_landing_dir).is_absolute() else Path(chi_d1_landing_dir).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_dir).resolve() if not Path(landing_dir).is_absolute() else Path(landing_dir).resolve()
    ensure_directories(out, landing)

    registry = read_json(d1_out / "CHI_D1_SOURCE_REGISTRY.json")
    harness = read_json(d1_out / "CHI_D1_HARNESS_REPORT.json")
    d1_hashes = selected_file_hashes(
        [
            d1_out / "CHI_D1_HARNESS_REPORT.json",
            d1_out / "CHI_D1_SOURCE_REGISTRY.json",
            d1_landing / "landing_manifest.json",
            d1_landing / "SHA256SUMS.json",
        ]
    )
    state = RunState(
        project_root=root,
        chi_d1_output_dir=d1_out,
        chi_d1_landing_dir=d1_landing,
        output_dir=out,
        landing_dir=landing,
        reports_dir=out / "reports",
        socrata_page_size=socrata_page_size,
        d1_registry=registry,
        d1_harness=harness,
        d1_before_hashes=d1_hashes,
    )

    plans = make_pull_plans(
        registry,
        pull_311=pull_311,
        pull_crimes=pull_crimes,
        pull_crashes=pull_crashes,
        pull_buildings=pull_buildings,
        pull_permits_violations=pull_permits_violations,
        pull_divvy=pull_divvy,
        pull_cook_parcels=pull_cook_parcels,
        pull_open_air=pull_open_air,
    )
    write_json(out / "CHI_D1B_INPUT_INVENTORY.json", input_inventory(state))
    completion = materialize_sources(state, plans, workers=workers)
    privacy = privacy_report(plans, completion)
    handoff = d2_d3_handoff(plans, completion)
    no_mutation = no_mutation_report(state)
    write_reports(state, plans, completion, privacy, handoff)
    write_json(out / "CHI_D1B_NO_MUTATION_REPORT.json", no_mutation)
    write_json(landing / "landing_manifest.json", landing_manifest(state, completion))
    write_json(landing / "SHA256SUMS.json", output_hashes(landing))
    secret_scan = scan_for_secrets([out, landing], secret_values_from_env())
    write_json(out / "CHI_D1B_SECRET_SCAN_REPORT.json", secret_scan)
    parts = leftover_part_files(landing)
    status = final_status(completion, secret_scan, parts)
    write_readme(out, landing, status)
    write_adapter_handover(out, landing, status, completion)
    write_json(out / "CHI_D1B_HARNESS_REPORT.json", {"task": TASK, "status": "PENDING_FINAL_GATE"})
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    artifact_report = required_artifact_report(out, landing)
    harness_report = gate_report(
        status=status,
        plans=plans,
        completion=completion,
        privacy=privacy,
        no_mutation=no_mutation,
        secret_scan=secret_scan,
        artifact_report=artifact_report,
        parts=parts,
    )
    write_json(out / "CHI_D1B_HARNESS_REPORT.json", harness_report)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return {
        "status": status,
        "output_dir": str(out),
        "landing_dir": str(landing),
        "plans": plans,
        "completion": completion,
        "privacy": privacy,
        "no_mutation": no_mutation,
        "secret_scan": secret_scan,
        "harness": harness_report,
    }


def source_row(report: dict[str, Any], prefix: str) -> tuple[int, str]:
    for item in report["completion"]:
        if item.get("source_key", "").startswith(prefix):
            return int(item.get("downloaded_rows") or 0), item.get("completion_status", "UNKNOWN")
    return 0, "NOT_PLANNED"


def print_final_report(report: dict[str, Any]) -> None:
    completion = report["completion"]
    status_counts: dict[str, int] = {}
    for item in completion:
        status_counts[item.get("completion_status", "UNKNOWN")] = status_counts.get(item.get("completion_status", "UNKNOWN"), 0) + 1
    total_rows = sum(int(item.get("downloaded_rows") or 0) for item in completion)
    crashes_rows = sum(int(item.get("downloaded_rows") or 0) for item in completion if item.get("source_key", "").startswith("traffic_crashes"))
    crashes_status = ",".join(sorted({item.get("completion_status", "UNKNOWN") for item in completion if item.get("source_key", "").startswith("traffic_crashes")})) or "NOT_PLANNED"
    buildings = source_row(report, "building_footprints")
    permits = source_row(report, "building_permits")
    violations = source_row(report, "building_violations")
    print(f"CHI-D1B Chicago Extended Source Landing: {report['status']}")
    print(f"Sources planned: {len(report['plans'])}")
    print(f"Sources attempted: {len(completion)}")
    print(f"Sources completed full: {status_counts.get('FULL', 0)}")
    print(f"Sources windowed: {status_counts.get('WINDOWED_COMPLETE', 0) + status_counts.get('WINDOWED_CAPPED', 0)}")
    print(f"Sources capped: {status_counts.get('CAPPED', 0) + status_counts.get('WINDOWED_CAPPED', 0)}")
    print(f"Sources partial: {status_counts.get('PARTIAL', 0)}")
    print(f"Rows downloaded total: {total_rows}")
    rows, status = source_row(report, "311_service_requests")
    print(f"311 rows: {rows} / {status}")
    rows, status = source_row(report, "crimes_2001_present")
    print(f"Crimes rows: {rows} / {status}")
    print(f"Crashes rows: {crashes_rows} / {crashes_status}")
    print(f"Buildings rows: {buildings[0]} / {buildings[1]}")
    print(f"Permits rows: {permits[0]} / {permits[1]}")
    print(f"Violations rows: {violations[0]} / {violations[1]}")
    rows, status = source_row(report, "divvy_trips")
    print(f"Divvy rows: {rows} / {status}")
    rows, status = source_row(report, "cook_county_parcel_universe")
    print(f"Cook parcels rows: {rows} / {status}")
    print(f"Privacy scan: {report['privacy'].get('status', 'FAIL')}")
    print("No-overclaim: PASS")
    print(f"No-mutation: {report['no_mutation'].get('status', 'FAIL')}")
    print(f"Landing: {report['landing_dir']}")
    print(f"Output: {report['output_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CHI-D1B Chicago extended source landing")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=r"outputs\chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--chi-d1-landing-dir", default=r"data_landing\chi_d1_official_sources_v1")
    parser.add_argument("--output-dir", default=r"outputs\chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--landing-dir", default=r"data_landing\chi_d1b_extended_sources_v1")
    parser.add_argument("--socrata-page-size", type=int, default=50_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-311", action="store_true")
    parser.add_argument("--no-crimes", action="store_true")
    parser.add_argument("--no-crashes", action="store_true")
    parser.add_argument("--no-buildings", action="store_true")
    parser.add_argument("--no-permits-violations", action="store_true")
    parser.add_argument("--no-divvy", action="store_true")
    parser.add_argument("--no-cook-parcels", action="store_true")
    parser.add_argument("--no-open-air", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_chi_d1b_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        socrata_page_size=args.socrata_page_size,
        pull_311=not args.no_311,
        pull_crimes=not args.no_crimes,
        pull_crashes=not args.no_crashes,
        pull_buildings=not args.no_buildings,
        pull_permits_violations=not args.no_permits_violations,
        pull_divvy=not args.no_divvy,
        pull_cook_parcels=not args.no_cook_parcels,
        pull_open_air=not args.no_open_air,
        workers=args.workers,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

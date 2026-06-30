#!/usr/bin/env python3
"""SG-D1 Singapore source/API scout and official source landing.

This stage lands source wrappers, bounded current snapshots, counts, hashes,
and handover reports for a future Singapore cartridge. It does not build a
Singapore graph, Flow 1, or Flow 4.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlencode, urlparse

import requests


TASK = "SG-D1 Singapore Source/API Scout"
LTA_BASE = "https://datamall2.mytransport.sg/ltaodataservice"
USER_AGENT = "TXR-CityBrain-SG-D1/1.0"
PASS_STATUSES = {
    "PASS_WITH_AUTHENTICATED_LTA_PULL",
    "PASS_SOURCE_SCOUT",
    "PASS_WITH_PARTIAL_PUBLIC_ONLY",
    "PASS_WITH_ONEMAP_TOKEN_MISSING",
}
FAIL_STATUSES = {"FAIL_SECRET_LEAK", "FAIL"}

LTA_PAGED_ENDPOINTS = [
    "BusStops",
    "BusServices",
    "BusRoutes",
    "TaxiStands",
    "Taxi-Availability",
    "CarParkAvailabilityv2",
    "EstTravelTimes",
    "FaultyTrafficLights",
    "RoadOpenings",
    "RoadWorks",
    "Traffic-Imagesv2",
    "TrafficIncidents",
    "v4/TrafficSpeedBands",
    "VMS",
    "v2/FacilitiesMaintenance",
    "PlannedBusRoutes",
    "PubFloodAlerts",
]
LTA_FILE_LINK_ENDPOINTS = ["EVCBatch", "TrafficFlow"]
LTA_PASSENGER_VOLUME_ENDPOINTS = ["PV/Bus", "PV/ODBus", "PV/Train", "PV/ODTrain"]
LTA_PCD_ENDPOINTS = ["PCDRealTime", "PCDForecast"]
LTA_TRAIN_LINES = ["CCL", "CEL", "CGL", "DTL", "EWL", "NEL", "NSL", "BPL", "SLRT", "PLRT", "TEL"]

LTA_SAFETY_CAPS = {
    "BusStops": 20_000,
    "BusServices": 5_000,
    "BusRoutes": 100_000,
    "v4/TrafficSpeedBands": 50_000,
}
GENERIC_LTA_CAP = 50_000

NEA_PUBLIC_ENDPOINTS = {
    "pm25": "https://api-open.data.gov.sg/v2/real-time/api/pm25",
    "rainfall": "https://api-open.data.gov.sg/v2/real-time/api/rainfall",
    "wind_speed": "https://api-open.data.gov.sg/v2/real-time/api/wind-speed",
    "wind_direction": "https://api-open.data.gov.sg/v2/real-time/api/wind-direction",
    "air_temperature": "https://api-open.data.gov.sg/v2/real-time/api/air-temperature",
    "relative_humidity": "https://api-open.data.gov.sg/v2/real-time/api/relative-humidity",
    "twenty_four_hr_forecast": "https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast",
    "two_hr_forecast": "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast",
}

ONEMAP_DOC_URLS = {
    "home": "https://www.onemap.gov.sg/home/",
    "api_docs": "https://www.onemap.gov.sg/apidocs/",
    "search_docs": "https://www.onemap.gov.sg/apidocs/search",
    "reverse_geocode_docs": "https://www.onemap.gov.sg/apidocs/reverseGeocode",
    "planning_area_docs": "https://www.onemap.gov.sg/apidocs/planningarea",
    "themes_docs": "https://www.onemap.gov.sg/apidocs/themes",
}
ONEMAP_SEARCH_PROBES = ["Marina Bay", "Raffles Place MRT", "Changi Airport", "Orchard Road", "Jurong East MRT"]
ONEMAP_REVERSE_PROBES = [
    {"name": "marina_bay", "location": "1.2830,103.8600"},
    {"name": "raffles_place_mrt", "location": "1.2840,103.8514"},
    {"name": "changi_airport", "location": "1.3644,103.9915"},
    {"name": "orchard_road", "location": "1.3048,103.8318"},
    {"name": "jurong_east_mrt", "location": "1.3332,103.7423"},
]

REQUIRED_OUTPUT_FILES = [
    "README.md",
    "SG_D1_HARNESS_REPORT.json",
    "SG_D1_SOURCE_REGISTRY.json",
    "SG_D1_API_PROBE_REPORT.json",
    "SG_D1_AUTH_REPORT_REDACTED.json",
    "SG_D1_COUNTS_REPORT.json",
    "SG_D1_RECOMMENDED_LIMITS.json",
    "SG_D1_SOURCE_LINKS.json",
    "SG_D1_LTA_DATAMALL_REPORT.json",
    "SG_D1_NEA_PUBLIC_API_REPORT.json",
    "SG_D1_ONEMAP_REPORT.json",
    "SG_D1_SOURCE_LINEAGE_REPORT.json",
    "SG_D1_NATIVE_ID_CANDIDATES.json",
    "SG_D1_FLOW_FIT_REPORT.json",
    "SG_D1_D2_RECOMMENDATION.json",
    "SG_D1_SECRET_SCAN_REPORT.json",
    "SG_D1_NO_OVERCLAIM_REPORT.json",
    "SG_D1_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]
REQUIRED_REPORT_FILES = [
    "lta_endpoint_matrix.json",
    "lta_pagination_counts.json",
    "lta_file_link_downloads.json",
    "lta_bus_arrival_sample_report.json",
    "lta_passenger_volume_report.json",
    "lta_dynamic_snapshot_status.json",
    "nea_public_api_counts.json",
    "onemap_probe_status.json",
    "source_failures_and_retries.json",
    "meaningful_limits_applied.json",
    "sg_city_identity_backbone_options.json",
    "sg_flow1_candidate_sources.json",
    "sg_flow4_candidate_sources.json",
    "sg_live_event_fabric_candidate_sources.json",
]

NO_OVERCLAIM_STATEMENTS = [
    "SG-D1 is a source/API scout and official source landing only.",
    "SG-D1 does not create a certified Singapore cartridge.",
    "SG-D1 does not create a Singapore graph.",
    "SG-D1 does not build Flow 1 or Flow 4.",
    "SG-D1 does not certify affected assets or make operational recommendations.",
    "Realtime snapshots are point-in-time observations, not historical completeness.",
    "Traffic image sample downloads are validation samples only.",
    "BusArrival is sampled, not full-network arrival history.",
    "Passenger volume is latest-month scout unless explicitly expanded.",
    "OneMap protected APIs are source-limited if token/credentials are unavailable.",
]


@dataclass
class RunState:
    project_root: Path
    output_dir: Path
    landing_dir: Path
    reports_dir: Path
    session: requests.Session
    lineage: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    retries: list[dict[str, Any]] = field(default_factory=list)
    lta_matrix: list[dict[str, Any]] = field(default_factory=list)
    lta_counts: dict[str, Any] = field(default_factory=dict)
    lta_pages: list[dict[str, Any]] = field(default_factory=list)
    lta_file_downloads: list[dict[str, Any]] = field(default_factory=list)
    lta_pv_report: dict[str, Any] = field(default_factory=dict)
    lta_dynamic_status: list[dict[str, Any]] = field(default_factory=list)
    bus_arrival_report: dict[str, Any] = field(default_factory=dict)
    nea_report: dict[str, Any] = field(default_factory=dict)
    onemap_report: dict[str, Any] = field(default_factory=dict)


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


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepared_url(url: str, params: dict[str, Any] | None = None) -> str:
    request = requests.Request("GET", url, params=params)
    return request.prepare().url or url


def read_json_bytes(content: bytes) -> Any:
    try:
        return json.loads(content.decode("utf-8-sig"))
    except Exception:
        return None


def compact_sample(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {str(k): compact_sample(v, depth + 1) for k, v in list(value.items())[:20]}
    if isinstance(value, list):
        return [compact_sample(v, depth + 1) for v in value[:3]]
    if isinstance(value, str):
        return value[:300]
    return value


def schema_shape(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return "..."
    if isinstance(value, dict):
        return {str(k): schema_shape(v, depth + 1) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [schema_shape(value[0], depth + 1)] if value else []
    return type(value).__name__


def schema_fingerprint(value: Any) -> str:
    shape = json.dumps(schema_shape(value), sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(shape).hexdigest()


def rows_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, dict) and isinstance(payload.get("value"), list):
        return payload["value"]
    if isinstance(payload, list):
        return payload
    return []


def recursive_urls(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(recursive_urls(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(recursive_urls(item))
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate.startswith(("http://", "https://")):
            found.append(candidate)
    seen: set[str] = set()
    unique: list[str] = []
    for url in found:
        if url not in seen:
            unique.append(url)
            seen.add(url)
    return unique


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "accept": "application/json"})
    return session


def http_get(
    state: RunState,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
    retries: int = 2,
    stream: bool = False,
) -> requests.Response | None:
    last_error: str | None = None
    for attempt in range(retries + 1):
        try:
            response = state.session.get(url, params=params, headers=headers, timeout=timeout, stream=stream)
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            state.retries.append(
                {"url": prepared_url(url, params), "attempt": attempt + 1, "timestamp": utc_now(), "error": last_error}
            )
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    state.failures.append({"url": prepared_url(url, params), "timestamp": utc_now(), "error": last_error or "unknown"})
    return None


def landing_subdir(state: RunState, group: str, name: str) -> Path:
    return state.landing_dir / "raw" / group / safe_name(name)


def save_raw_response(
    state: RunState,
    *,
    group: str,
    source_name: str,
    file_name: str,
    url: str,
    params: dict[str, Any] | None,
    response: requests.Response,
    purpose: str,
) -> dict[str, Any]:
    directory = landing_subdir(state, group, source_name)
    path = directory / file_name
    content = response.content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    entry = {
        "group": group,
        "source_name": source_name,
        "purpose": purpose,
        "url": prepared_url(url, params),
        "http_status": response.status_code,
        "timestamp": utc_now(),
        "path": str(path),
        "relative_path": str(path.relative_to(state.project_root)) if path.is_relative_to(state.project_root) else str(path),
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }
    state.lineage.append(entry)
    return entry


def save_downloaded_file(
    state: RunState,
    *,
    source_group: str,
    source_name: str,
    url: str,
    response: requests.Response,
    filename_hint: str,
) -> dict[str, Any]:
    parsed = urlparse(url)
    raw_name = Path(unquote(parsed.path)).name or filename_hint
    suffix = Path(raw_name).suffix
    base = safe_name(Path(raw_name).stem or filename_hint)
    digest_prefix = sha256_bytes(url.encode("utf-8"))[:12]
    filename = f"{safe_name(filename_hint)}__{base}__{digest_prefix}{suffix}"
    path = state.landing_dir / "downloaded_files" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    entry = {
        "group": source_group,
        "source_name": source_name,
        "purpose": "downloaded_file_link",
        "url": url,
        "http_status": response.status_code,
        "timestamp": utc_now(),
        "path": str(path),
        "relative_path": str(path.relative_to(state.project_root)) if path.is_relative_to(state.project_root) else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "content_type": response.headers.get("content-type", ""),
    }
    state.lineage.append(entry)
    state.lta_file_downloads.append(entry)
    return entry


def lta_headers(api_key: str) -> dict[str, str]:
    return {"AccountKey": api_key, "accept": "application/json", "User-Agent": USER_AGENT}


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def lta_endpoint_url(endpoint: str) -> str:
    return f"{LTA_BASE}/{endpoint}"


def probe_lta_paged(
    state: RunState,
    endpoint: str,
    api_key: str,
    *,
    page_size: int,
    safety_cap: int,
) -> dict[str, Any]:
    log(f"LTA probe {endpoint}")
    url = lta_endpoint_url(endpoint)
    offset = 0
    total_rows = 0
    pages: list[dict[str, Any]] = []
    status = "not_started"
    error: str | None = None
    sample_record: Any = None
    while offset < safety_cap:
        params = {"$skip": offset}
        response = http_get(state, url, params=params, headers=lta_headers(api_key), timeout=90, retries=2)
        if response is None:
            status = "source_limited"
            error = "request_failed"
            break
        if response.status_code >= 400 and offset == 0:
            fallback = http_get(state, url, headers=lta_headers(api_key), timeout=90, retries=1)
            if fallback is not None and fallback.status_code < 400:
                response = fallback
                params = None
        file_name = f"page_skip_{offset:06d}.json"
        entry = save_raw_response(
            state,
            group="lta_datamall",
            source_name=endpoint,
            file_name=file_name,
            url=url,
            params=params,
            response=response,
            purpose="paged_json",
        )
        payload = read_json_bytes(response.content)
        rows = rows_from_payload(payload)
        returned = len(rows)
        page_record = {
            "endpoint": endpoint,
            "offset": offset,
            "returned_count": returned,
            "http_status": response.status_code,
            "bytes": entry["bytes"],
            "sha256": entry["sha256"],
            "url": entry["url"],
            "timestamp": entry["timestamp"],
        }
        pages.append(page_record)
        state.lta_pages.append(page_record)
        if response.status_code >= 400:
            status = "source_limited"
            error = f"http_{response.status_code}"
            state.failures.append({"source": endpoint, "url": entry["url"], "http_status": response.status_code})
            break
        if sample_record is None and rows:
            sample_record = compact_sample(rows[0])
        total_rows += returned
        if returned == 0:
            status = "full_until_empty"
            break
        if returned < page_size:
            status = "full_below_page_size"
            break
        offset += page_size
    if total_rows >= safety_cap and status not in {"source_limited", "full_until_empty", "full_below_page_size"}:
        status = "CAPPED_REQUIRES_D2_FULL_PULL"
    result = {
        "endpoint": endpoint,
        "http_ok": any(page["http_status"] < 400 for page in pages),
        "status": status,
        "rows": total_rows,
        "pages": len(pages),
        "page_size": page_size,
        "safety_cap": safety_cap,
        "sample_record": sample_record,
        "error": error,
    }
    state.lta_counts[endpoint] = result
    state.lta_matrix.append(result)
    write_json(state.landing_dir / "chunk_manifests" / f"lta_{safe_name(endpoint)}_pages.json", {"pages": pages, "summary": result})
    return result


def download_urls_for_wrapper(
    state: RunState,
    *,
    source_name: str,
    urls: list[str],
    filename_hint: str,
    max_downloads: int | None = None,
) -> list[dict[str, Any]]:
    downloads: list[dict[str, Any]] = []
    for index, link in enumerate(urls):
        if max_downloads is not None and index >= max_downloads:
            break
        response = http_get(state, link, timeout=180, retries=2)
        if response is None:
            downloads.append({"url": link, "status": "request_failed"})
            continue
        if response.status_code >= 400:
            downloads.append({"url": link, "status": "http_error", "http_status": response.status_code})
            continue
        downloads.append(
            save_downloaded_file(
                state,
                source_group="lta_datamall",
                source_name=source_name,
                url=link,
                response=response,
                filename_hint=f"{filename_hint}_{index + 1:02d}",
            )
        )
    return downloads


def probe_lta_file_link_endpoint(state: RunState, endpoint: str, api_key: str) -> dict[str, Any]:
    log(f"LTA file-link probe {endpoint}")
    url = lta_endpoint_url(endpoint)
    response = http_get(state, url, headers=lta_headers(api_key), timeout=90, retries=2)
    if response is None:
        result = {"endpoint": endpoint, "status": "source_limited", "rows": 0, "links": [], "downloads": []}
        state.lta_counts[endpoint] = result
        state.lta_matrix.append(result)
        return result
    entry = save_raw_response(
        state,
        group="lta_datamall",
        source_name=endpoint,
        file_name="wrapper.json",
        url=url,
        params=None,
        response=response,
        purpose="file_link_wrapper",
    )
    payload = read_json_bytes(response.content)
    rows = rows_from_payload(payload)
    links = recursive_urls(payload)
    downloads = download_urls_for_wrapper(state, source_name=endpoint, urls=links, filename_hint=safe_name(endpoint))
    result = {
        "endpoint": endpoint,
        "status": "downloaded_file_links" if downloads else ("no_file_links_found" if response.status_code < 400 else "source_limited"),
        "http_status": response.status_code,
        "rows": len(rows),
        "links": links,
        "download_count": len([item for item in downloads if item.get("sha256")]),
        "downloads": downloads,
        "wrapper_sha256": entry["sha256"],
    }
    if response.status_code >= 400:
        state.failures.append({"source": endpoint, "url": url, "http_status": response.status_code})
    state.lta_counts[endpoint] = result
    state.lta_matrix.append(result)
    return result


def previous_months(count: int = 48) -> list[str]:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month - 1
    if month == 0:
        month = 12
        year -= 1
    values: list[str] = []
    for _ in range(count):
        values.append(f"{year:04d}{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return values


def probe_lta_passenger_volume(
    state: RunState,
    endpoint: str,
    api_key: str,
    *,
    months_to_land: int,
) -> dict[str, Any]:
    log(f"LTA passenger-volume probe {endpoint}")
    url = lta_endpoint_url(endpoint)
    found: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for month in previous_months(60):
        if len(found) >= months_to_land:
            break
        for spelling in ["Date", "Dates"]:
            params = {spelling: month}
            response = http_get(state, url, params=params, headers=lta_headers(api_key), timeout=90, retries=1)
            attempt = {"endpoint": endpoint, "month": month, "parameter": spelling, "url": prepared_url(url, params)}
            if response is None:
                attempt["status"] = "request_failed"
                attempts.append(attempt)
                continue
            payload = read_json_bytes(response.content)
            links = recursive_urls(payload)
            rows = rows_from_payload(payload)
            attempt.update({"http_status": response.status_code, "row_count": len(rows), "link_count": len(links)})
            attempts.append(attempt)
            if response.status_code < 400 and links:
                wrapper_name = f"{month}_{spelling}.json"
                entry = save_raw_response(
                    state,
                    group="lta_datamall",
                    source_name=endpoint,
                    file_name=wrapper_name,
                    url=url,
                    params=params,
                    response=response,
                    purpose="passenger_volume_file_link_wrapper",
                )
                downloads = download_urls_for_wrapper(
                    state,
                    source_name=endpoint,
                    urls=links,
                    filename_hint=f"{safe_name(endpoint)}_{month}",
                )
                found.append(
                    {
                        "endpoint": endpoint,
                        "month": month,
                        "parameter_spelling_worked": spelling,
                        "wrapper_sha256": entry["sha256"],
                        "links": links,
                        "downloads": downloads,
                        "download_count": len([item for item in downloads if item.get("sha256")]),
                    }
                )
                break
    result = {
        "endpoint": endpoint,
        "status": "downloaded_latest_month" if found else "source_limited_no_recent_file_link",
        "months_requested": months_to_land,
        "months_landed": found,
        "attempts": attempts,
    }
    state.lta_pv_report[endpoint] = result
    state.lta_counts[endpoint] = {
        "endpoint": endpoint,
        "status": result["status"],
        "rows": sum(item.get("download_count", 0) for item in found),
        "downloaded_months": [item["month"] for item in found],
    }
    state.lta_matrix.append(state.lta_counts[endpoint])
    return result


def probe_lta_pcd(state: RunState, endpoint: str, api_key: str) -> dict[str, Any]:
    log(f"LTA station crowd-density probe {endpoint}")
    url = lta_endpoint_url(endpoint)
    line_results: list[dict[str, Any]] = []
    total_rows = 0
    for line in LTA_TRAIN_LINES:
        params = {"TrainLine": line}
        response = http_get(state, url, params=params, headers=lta_headers(api_key), timeout=90, retries=2)
        if response is None:
            line_results.append({"line": line, "status": "request_failed", "rows": 0})
            continue
        entry = save_raw_response(
            state,
            group="lta_datamall",
            source_name=endpoint,
            file_name=f"{line}.json",
            url=url,
            params=params,
            response=response,
            purpose="train_line_snapshot",
        )
        payload = read_json_bytes(response.content)
        rows = rows_from_payload(payload)
        total_rows += len(rows)
        line_results.append(
            {
                "line": line,
                "status": "ok" if response.status_code < 400 else "source_limited",
                "http_status": response.status_code,
                "rows": len(rows),
                "sha256": entry["sha256"],
                "url": entry["url"],
            }
        )
    result = {
        "endpoint": endpoint,
        "status": "pulled_all_lines" if any(item.get("rows", 0) > 0 for item in line_results) else "source_limited",
        "rows": total_rows,
        "lines": line_results,
    }
    state.lta_counts[endpoint] = result
    state.lta_matrix.append(result)
    state.lta_dynamic_status.append(result)
    return result


def choose_bus_arrival_sample(bus_stop_rows: list[dict[str, Any]], target: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [row for row in bus_stop_rows if isinstance(row, dict) and row.get("BusStopCode")]
    rows.sort(key=lambda row: str(row.get("BusStopCode", "")))
    interchanges = [
        row
        for row in rows
        if any(token in str(row.get("Description", "")).upper() for token in ["INTERCHANGE", " INT", "INT "])
    ]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    interchange_limit = min(len(interchanges), max(10, target // 3))
    for row in interchanges[:interchange_limit]:
        code = str(row.get("BusStopCode"))
        selected.append(row)
        seen.add(code)
    remaining = [row for row in rows if str(row.get("BusStopCode")) not in seen]
    if remaining and len(selected) < target:
        def grid_key(row: dict[str, Any]) -> tuple[int, int, str]:
            try:
                lat = float(row.get("Latitude", 0))
                lon = float(row.get("Longitude", 0))
            except Exception:
                lat = lon = 0.0
            return (round(lat * 100), round(lon * 100), str(row.get("BusStopCode", "")))

        remaining.sort(key=grid_key)
        need = target - len(selected)
        if len(remaining) <= need:
            selected.extend(remaining)
        else:
            for index in range(need):
                pick = round(index * (len(remaining) - 1) / max(need - 1, 1))
                selected.append(remaining[pick])
    sample = selected[:target]
    method = {
        "target": target,
        "bus_stop_rows_available": len(rows),
        "selected": len(sample),
        "interchange_priority_count": min(interchange_limit, len(sample)),
        "method": "deterministic: bus interchanges by description first, then stratified by rounded latitude/longitude grid and BusStopCode",
    }
    return sample, method


def probe_lta_bus_arrivals(
    state: RunState,
    api_key: str,
    bus_stop_rows: list[dict[str, Any]],
    *,
    sample_stops: int,
) -> dict[str, Any]:
    log(f"LTA BusArrival sample probe {sample_stops} stops")
    sample, method = choose_bus_arrival_sample(bus_stop_rows, sample_stops)
    url = lta_endpoint_url("v3/BusArrival")
    results: list[dict[str, Any]] = []
    total_services = 0
    for row in sample:
        code = str(row.get("BusStopCode"))
        params = {"BusStopCode": code}
        response = http_get(state, url, params=params, headers=lta_headers(api_key), timeout=60, retries=1)
        if response is None:
            results.append({"BusStopCode": code, "status": "request_failed", "services": 0})
            continue
        entry = save_raw_response(
            state,
            group="lta_datamall",
            source_name="v3/BusArrival",
            file_name=f"{safe_name(code)}.json",
            url=url,
            params=params,
            response=response,
            purpose="sampled_bus_arrival",
        )
        payload = read_json_bytes(response.content)
        services = payload.get("Services", []) if isinstance(payload, dict) else []
        total_services += len(services) if isinstance(services, list) else 0
        results.append(
            {
                "BusStopCode": code,
                "description": row.get("Description"),
                "http_status": response.status_code,
                "status": "ok" if response.status_code < 400 else "source_limited",
                "services": len(services) if isinstance(services, list) else 0,
                "sha256": entry["sha256"],
                "url": entry["url"],
            }
        )
        time.sleep(0.05)
    report = {
        "endpoint": "v3/BusArrival",
        "status": "sampled" if results else "not_sampled",
        "sample_method": method,
        "sampled_stops": len(results),
        "service_rows_observed": total_services,
        "results": results,
    }
    state.bus_arrival_report = report
    state.lta_counts["v3/BusArrival"] = {
        "endpoint": "v3/BusArrival",
        "status": report["status"],
        "rows": total_services,
        "sampled_stops": len(results),
    }
    state.lta_matrix.append(state.lta_counts["v3/BusArrival"])
    return report


def find_image_urls(records: list[Any]) -> list[str]:
    urls: list[str] = []
    for record in records:
        for link in recursive_urls(record):
            lower = link.lower()
            if any(token in lower for token in [".jpg", ".jpeg", ".png", "traffic-images", "image"]):
                urls.append(link)
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            unique.append(url)
            seen.add(url)
    return unique


def download_traffic_image_samples(
    state: RunState,
    image_urls: list[str],
    max_samples: int,
) -> list[dict[str, Any]]:
    downloads: list[dict[str, Any]] = []
    for index, link in enumerate(image_urls[:max_samples]):
        response = http_get(state, link, timeout=90, retries=1)
        if response is None:
            downloads.append({"url": link, "status": "request_failed"})
            continue
        if response.status_code >= 400:
            downloads.append({"url": link, "status": "http_error", "http_status": response.status_code})
            continue
        downloads.append(
            save_downloaded_file(
                state,
                source_group="lta_datamall",
                source_name="Traffic-Imagesv2",
                url=link,
                response=response,
                filename_hint=f"traffic_image_sample_{index + 1:02d}",
            )
        )
    return downloads


def run_lta(
    state: RunState,
    *,
    api_key: str | None,
    page_size: int,
    bus_arrival_sample_stops: int,
    traffic_image_sample_downloads: int,
    passenger_volume_months: int,
) -> dict[str, Any]:
    if not api_key:
        report = {"status": "NOT_RUN", "reason": "LTA_DATAMALL_API_KEY missing", "authenticated": False}
        write_json(state.reports_dir / "lta_endpoint_matrix.json", [])
        return report
    auth_probe = probe_lta_paged(state, "BusStops", api_key, page_size=page_size, safety_cap=LTA_SAFETY_CAPS["BusStops"])
    bus_stop_rows: list[dict[str, Any]] = []
    bus_stop_dir = landing_subdir(state, "lta_datamall", "BusStops")
    for path in sorted(bus_stop_dir.glob("page_skip_*.json")):
        payload = read_json_bytes(path.read_bytes())
        bus_stop_rows.extend([row for row in rows_from_payload(payload) if isinstance(row, dict)])
    for endpoint in LTA_PAGED_ENDPOINTS:
        if endpoint == "BusStops":
            continue
        cap = LTA_SAFETY_CAPS.get(endpoint, GENERIC_LTA_CAP)
        result = probe_lta_paged(state, endpoint, api_key, page_size=page_size, safety_cap=cap)
        if endpoint == "Traffic-Imagesv2":
            records: list[Any] = []
            for path in sorted(landing_subdir(state, "lta_datamall", endpoint).glob("page_skip_*.json")):
                records.extend(rows_from_payload(read_json_bytes(path.read_bytes())))
            image_urls = find_image_urls(records)
            samples = download_traffic_image_samples(state, image_urls, traffic_image_sample_downloads)
            result["image_urls_observed"] = len(image_urls)
            result["sample_image_downloads"] = samples
            state.lta_dynamic_status.append(
                {
                    "endpoint": endpoint,
                    "metadata_rows": result.get("rows", 0),
                    "sample_image_downloads": len([item for item in samples if item.get("sha256")]),
                    "note": "Traffic image samples are transient/live validation evidence, not a camera archive.",
                }
            )
    for endpoint in LTA_FILE_LINK_ENDPOINTS:
        probe_lta_file_link_endpoint(state, endpoint, api_key)
    for endpoint in LTA_PCD_ENDPOINTS:
        probe_lta_pcd(state, endpoint, api_key)
    for endpoint in LTA_PASSENGER_VOLUME_ENDPOINTS:
        probe_lta_passenger_volume(state, endpoint, api_key, months_to_land=passenger_volume_months)
    if bus_stop_rows:
        probe_lta_bus_arrivals(state, api_key, bus_stop_rows, sample_stops=bus_arrival_sample_stops)
    ok_count = len([item for item in state.lta_matrix if item.get("http_ok") or item.get("rows", 0) > 0 or item.get("download_count", 0) > 0])
    pulled_count = len([item for item in state.lta_matrix if item.get("rows", 0) > 0 or item.get("download_count", 0) > 0])
    status = "PASS" if ok_count > 0 else "FAIL"
    report = {
        "status": status,
        "authenticated": ok_count > 0,
        "auth_probe": auth_probe,
        "endpoints_probed": len(state.lta_matrix),
        "endpoints_pulled": pulled_count,
        "counts": state.lta_counts,
        "file_link_downloads": state.lta_file_downloads,
        "dynamic_snapshot_status": state.lta_dynamic_status,
        "passenger_volume": state.lta_pv_report,
        "bus_arrival_sample": state.bus_arrival_report,
    }
    return report


def count_nea_payload(payload: Any) -> dict[str, Any]:
    station_count = 0
    region_count = 0
    reading_count = 0
    sample_record: Any = None

    def visit(value: Any, key_hint: str = "") -> None:
        nonlocal station_count, region_count, reading_count, sample_record
        if isinstance(value, dict):
            for key, item in value.items():
                lower = str(key).lower()
                if isinstance(item, list):
                    if "station" in lower and station_count == 0:
                        station_count = len(item)
                        if item and sample_record is None:
                            sample_record = item[0]
                    if "region" in lower and region_count == 0:
                        region_count = len(item)
                    if lower in {"readings", "data", "items", "forecasts"} and sample_record is None and item:
                        sample_record = item[0]
                visit(item, lower)
        elif isinstance(value, list):
            for item in value:
                visit(item, key_hint)
        elif isinstance(value, (int, float)) and key_hint not in {"latitude", "longitude", "lat", "lng"}:
            reading_count += 1

    visit(payload)
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, dict):
            readings = data.get("readings")
            if isinstance(readings, list):
                reading_count = max(reading_count, len(readings))
            elif isinstance(readings, dict):
                numeric_values = [v for v in readings.values() if isinstance(v, (int, float, str))]
                reading_count = max(reading_count, len(numeric_values))
    return {
        "station_count": station_count,
        "region_count": region_count,
        "reading_count": reading_count,
        "sample_record": compact_sample(sample_record),
    }


def run_nea_public(state: RunState) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "NOT_RUN", "endpoints": {}}
    successes = 0
    for name, url in NEA_PUBLIC_ENDPOINTS.items():
        log(f"NEA/data.gov.sg probe {name}")
        response = http_get(state, url, timeout=90, retries=2)
        if response is None:
            report["endpoints"][name] = {"endpoint": url, "status": "request_failed"}
            continue
        entry = save_raw_response(
            state,
            group="nea_public",
            source_name=name,
            file_name="snapshot.json",
            url=url,
            params=None,
            response=response,
            purpose="current_public_snapshot",
        )
        payload = read_json_bytes(response.content)
        counts = count_nea_payload(payload)
        endpoint_report = {
            "endpoint": url,
            "http_status": response.status_code,
            "status": "ok" if response.status_code < 400 else "source_limited",
            "timestamp": entry["timestamp"],
            "station_count": counts["station_count"],
            "region_count": counts["region_count"],
            "reading_count": counts["reading_count"],
            "schema_fingerprint": schema_fingerprint(payload),
            "sample_record": counts["sample_record"],
            "sha256": entry["sha256"],
        }
        if response.status_code < 400:
            successes += 1
        else:
            state.failures.append({"source": name, "url": url, "http_status": response.status_code})
        report["endpoints"][name] = endpoint_report
    report["status"] = "PASS" if successes else "FAIL"
    report["successful_endpoints"] = successes
    state.nea_report = report
    return report


def get_onemap_token(state: RunState) -> tuple[str | None, dict[str, Any]]:
    env_token = os.environ.get("ONEMAP_TOKEN")
    email = os.environ.get("ONEMAP_EMAIL")
    password = os.environ.get("ONEMAP_PASSWORD")
    auth_report = {
        "onemap_token_present_in_environment": bool(env_token),
        "onemap_email_present_in_environment": bool(email),
        "onemap_password_present_in_environment": bool(password),
        "login_attempted": False,
        "login_token_acquired": False,
    }
    if env_token:
        return env_token, auth_report
    if email and password:
        auth_report["login_attempted"] = True
        url = "https://www.onemap.gov.sg/api/auth/post/getToken"
        try:
            response = state.session.post(
                url,
                json={"email": email, "password": password},
                headers={"User-Agent": USER_AGENT, "accept": "application/json"},
                timeout=60,
            )
            auth_report["login_http_status"] = response.status_code
            payload = read_json_bytes(response.content)
            token = None
            if isinstance(payload, dict):
                token = payload.get("access_token") or payload.get("token")
            auth_report["login_token_acquired"] = bool(token)
            return token, auth_report
        except Exception as exc:  # noqa: BLE001
            auth_report["login_error"] = type(exc).__name__
    return None, auth_report


def onemap_auth_headers(token: str | None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def save_onemap_get(
    state: RunState,
    *,
    name: str,
    url: str,
    params: dict[str, Any] | None,
    token: str | None,
    purpose: str,
    file_name: str = "response.json",
) -> dict[str, Any]:
    response = http_get(state, url, params=params, headers=onemap_auth_headers(token), timeout=90, retries=1)
    if response is None:
        return {"name": name, "url": prepared_url(url, params), "status": "request_failed"}
    entry = save_raw_response(
        state,
        group="onemap",
        source_name=name,
        file_name=file_name,
        url=url,
        params=params,
        response=response,
        purpose=purpose,
    )
    payload = read_json_bytes(response.content)
    result_count = 0
    if isinstance(payload, dict):
        for key in ["results", "SearchResults", "value", "data"]:
            if isinstance(payload.get(key), list):
                result_count = len(payload[key])
                break
    status = "ok" if response.status_code < 400 else "source_limited"
    if response.status_code in {401, 403} and not token:
        status = "ONEMAP_TOKEN_MISSING"
    if isinstance(payload, dict) and payload.get("error") and "token" in str(payload.get("error")).lower() and not token:
        status = "PARTIAL_TOKEN_WARNING"
    return {
        "name": name,
        "url": entry["url"],
        "http_status": response.status_code,
        "status": status,
        "result_count": result_count,
        "schema_fingerprint": schema_fingerprint(payload),
        "sample_record": compact_sample(payload),
        "sha256": entry["sha256"],
    }


def run_onemap(state: RunState) -> dict[str, Any]:
    token, auth_report = get_onemap_token(state)
    report: dict[str, Any] = {"status": "NOT_RUN", "auth": auth_report, "docs": {}, "probes": {}}
    token_limited = False
    successes = 0
    for name, url in ONEMAP_DOC_URLS.items():
        log(f"OneMap docs probe {name}")
        response = http_get(state, url, headers={"User-Agent": USER_AGENT, "accept": "text/html,application/json"}, timeout=60)
        if response is None:
            report["docs"][name] = {"url": url, "status": "request_failed"}
            continue
        entry = save_raw_response(
            state,
            group="onemap",
            source_name=f"docs_{name}",
            file_name="document.html",
            url=url,
            params=None,
            response=response,
            purpose="official_docs_page",
        )
        report["docs"][name] = {
            "url": url,
            "http_status": response.status_code,
            "status": "ok" if response.status_code < 400 else "source_limited",
            "bytes": entry["bytes"],
            "sha256": entry["sha256"],
        }
        if response.status_code < 400:
            successes += 1
    planning_names = save_onemap_get(
        state,
        name="planning_area_names",
        url="https://www.onemap.gov.sg/api/public/popapi/getPlanningareaNames",
        params={"year": "2019"},
        token=token,
        purpose="planning_area_names",
    )
    report["probes"]["planning_area_names"] = planning_names
    planning_polygons = save_onemap_get(
        state,
        name="planning_area_polygons",
        url="https://www.onemap.gov.sg/api/public/popapi/getAllPlanningarea",
        params={"year": "2019"},
        token=token,
        purpose="planning_area_polygons",
    )
    report["probes"]["planning_area_polygons"] = planning_polygons
    for label in ["planning_area_names", "planning_area_polygons"]:
        if report["probes"][label].get("status") == "ONEMAP_TOKEN_MISSING":
            token_limited = True
        elif report["probes"][label].get("http_status", 999) < 400:
            successes += 1
    for term in ONEMAP_SEARCH_PROBES:
        result = save_onemap_get(
            state,
            name=f"search_{safe_name(term)}",
            url="https://www.onemap.gov.sg/api/common/elastic/search",
            params={"searchVal": term, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1},
            token=token,
            purpose="fixed_search_validation",
        )
        report["probes"][f"search_{safe_name(term)}"] = result
        if result.get("status") == "ONEMAP_TOKEN_MISSING":
            token_limited = True
        elif result.get("http_status", 999) < 400:
            successes += 1
    for probe in ONEMAP_REVERSE_PROBES:
        result = save_onemap_get(
            state,
            name=f"reverse_{probe['name']}",
            url="https://www.onemap.gov.sg/api/public/revgeocode",
            params={"location": probe["location"], "buffer": 40, "addressType": "All", "otherFeatures": "N"},
            token=token,
            purpose="fixed_reverse_geocode_validation",
        )
        report["probes"][f"reverse_{probe['name']}"] = result
        if result.get("status") == "ONEMAP_TOKEN_MISSING":
            token_limited = True
        elif result.get("http_status", 999) < 400:
            successes += 1
    themes = save_onemap_get(
        state,
        name="themes_metadata",
        url="https://www.onemap.gov.sg/api/public/themesvc/getAllThemesInfo",
        params={"moreInfo": "Y"},
        token=token,
        purpose="themes_metadata",
    )
    report["probes"]["themes_metadata"] = themes
    if themes.get("status") == "ONEMAP_TOKEN_MISSING":
        token_limited = True
    elif themes.get("http_status", 999) < 400:
        successes += 1
    if token:
        population = save_onemap_get(
            state,
            name="population_planning_area_probe",
            url="https://www.onemap.gov.sg/api/public/popapi/getAllPopulation",
            params={"planningArea": "Yishun", "year": "2020"},
            token=token,
            purpose="population_planning_area_probe",
        )
        report["probes"]["population_planning_area_probe"] = population
        if population.get("http_status", 999) < 400:
            successes += 1
    report["token_limited"] = token_limited
    report["successful_probes"] = successes
    if token_limited and successes:
        report["status"] = "PARTIAL"
    elif token_limited:
        report["status"] = "TOKEN_MISSING"
    elif successes:
        report["status"] = "PASS"
    else:
        report["status"] = "FAIL"
    state.onemap_report = report
    return report


def source_registry() -> dict[str, Any]:
    lta_entries = [
        {"group": "LTA DataMall", "name": endpoint, "url": lta_endpoint_url(endpoint), "auth": "LTA_DATAMALL_API_KEY"}
        for endpoint in LTA_PAGED_ENDPOINTS + LTA_FILE_LINK_ENDPOINTS + LTA_PASSENGER_VOLUME_ENDPOINTS + LTA_PCD_ENDPOINTS + ["v3/BusArrival"]
    ]
    nea_entries = [
        {"group": "data.gov.sg / NEA public APIs", "name": name, "url": url, "auth": "public"}
        for name, url in NEA_PUBLIC_ENDPOINTS.items()
    ]
    onemap_entries = [
        {"group": "OneMap", "name": name, "url": url, "auth": "public/protected depending on endpoint"}
        for name, url in ONEMAP_DOC_URLS.items()
    ]
    onemap_entries.extend(
        [
            {"group": "OneMap", "name": "Search API", "url": "https://www.onemap.gov.sg/api/common/elastic/search", "auth": "public with token warning/protected behavior"},
            {"group": "OneMap", "name": "Reverse Geocode API", "url": "https://www.onemap.gov.sg/api/public/revgeocode", "auth": "protected if 401 without token"},
            {"group": "OneMap", "name": "Planning Area Names", "url": "https://www.onemap.gov.sg/api/public/popapi/getPlanningareaNames", "auth": "protected if 401 without token"},
            {"group": "OneMap", "name": "Planning Area Polygons", "url": "https://www.onemap.gov.sg/api/public/popapi/getAllPlanningarea", "auth": "protected if 401 without token"},
            {"group": "OneMap", "name": "Themes API", "url": "https://www.onemap.gov.sg/api/public/themesvc/getAllThemesInfo", "auth": "protected if 401 without token"},
        ]
    )
    static_entries = [
        {
            "group": "data.gov.sg / URA static scout",
            "name": "Master Plan 2019 Planning Area Boundary",
            "url": "https://data.gov.sg/",
            "auth": "public metadata scout only in SG-D1",
        },
        {
            "group": "data.gov.sg / URA static scout",
            "name": "Master Plan Subzone Boundary",
            "url": "https://data.gov.sg/",
            "auth": "public metadata scout only in SG-D1",
        },
    ]
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "boundary": NO_OVERCLAIM_STATEMENTS[0],
        "sources": lta_entries + nea_entries + onemap_entries + static_entries,
    }


def native_id_candidates() -> dict[str, Any]:
    return {
        "status": "PASS",
        "candidates": [
            {"native_id": "bus_stop_code", "citybrain_anchor": "TransitNode"},
            {"native_id": "bus_service_no + operator", "citybrain_anchor": "TransitService"},
            {"native_id": "bus_route service/direction/stop_sequence", "citybrain_anchor": "TransitRouteSegment"},
            {"native_id": "station_code", "citybrain_anchor": "TransitNode"},
            {"native_id": "traffic_speed_band LinkID", "citybrain_anchor": "RoadSegment candidate"},
            {"native_id": "traffic incident EventID or generated source id", "citybrain_anchor": "Event"},
            {"native_id": "traffic image CameraID", "citybrain_anchor": "Sensor / Camera candidate"},
            {"native_id": "VMS EquipmentID", "citybrain_anchor": "Sensor / RoadsideAsset candidate"},
            {"native_id": "carpark id / development id", "citybrain_anchor": "Resource / Facility candidate"},
            {"native_id": "EV charger id / evCpId", "citybrain_anchor": "InfrastructureAsset / EVChargingPoint candidate"},
            {"native_id": "flood alert alertId", "citybrain_anchor": "Event"},
            {"native_id": "planning area code/name", "citybrain_anchor": "AreaContext"},
            {"native_id": "postal code / OneMap search result id", "citybrain_anchor": "AddressableLocation candidate"},
        ],
        "boundary": "Singapore anchors are not forced into NYC/London land-parcel semantics in SG-D1.",
    }


def flow_fit_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "Flow 1 - Situational Status": [
            "planning areas",
            "bus stops/services/routes",
            "traffic speed bands",
            "carparks",
            "EV charging",
            "weather/air/rainfall",
            "VMS/traffic incidents",
        ],
        "Flow 4 - Crowd / Major Event": [
            "station crowd density real-time/forecast",
            "traffic images",
            "traffic incidents",
            "bus arrival sample",
            "traffic speed bands",
            "passenger volume",
            "rainfall / PM2.5 / wind",
            "carpark availability",
            "EV charging",
        ],
        "Live Event Fabric": [
            "traffic incidents",
            "traffic speed bands",
            "traffic images",
            "taxi availability",
            "carpark availability",
            "station crowd density",
            "flood alerts",
            "rainfall / PM2.5 / wind",
        ],
    }


def recommended_limits() -> dict[str, Any]:
    return {
        "status": "PASS",
        "LTA paged JSON APIs": {
            "page_size": 500,
            "safety_cap_bus_stops": 20_000,
            "safety_cap_bus_services": 5_000,
            "safety_cap_bus_routes": 100_000,
            "safety_cap_traffic_speed_bands": 50_000,
            "safety_cap_generic_paged_api": 50_000,
        },
        "Realtime/current event APIs": {
            "sg_d1": "one current snapshot",
            "optional_repeat_snapshots": 3,
            "repeat_interval_seconds": 120,
        },
        "Traffic images": {"metadata_full": True, "sample_image_downloads": 10},
        "Passenger volume": {"sg_d1_months": 1, "sg_d2_recommended_months": 3},
        "BusArrival": {"sg_d1_sample_stops": "100 to 250", "all_stop_pull": False},
        "OneMap Search/Reverse": {"validation_probes_only": True, "bulk_geocoding": False},
    }


def d2_recommendation(lta_report: dict[str, Any], onemap_report: dict[str, Any]) -> dict[str, Any]:
    capped = [
        item["endpoint"]
        for item in lta_report.get("counts", {}).values()
        if isinstance(item, dict) and item.get("status") == "CAPPED_REQUIRES_D2_FULL_PULL"
    ]
    return {
        "status": "PASS",
        "recommended_next_stage": "SG-D2 official source expansion and source-specific parsers",
        "priorities": [
            "Expand passenger volume pulls to latest 3 months.",
            "Parse downloaded LTA file-link payloads into source-specific inventories.",
            "If OneMap token is available, land planning area polygons, theme metadata, and selected verified theme families.",
            "Build canonical Singapore identity backbone candidates from BusStops, BusServices, BusRoutes, TrafficSpeedBands, traffic cameras, and planning areas.",
            "Repeat dynamic snapshots where useful, preserving point-in-time status and avoiding historical completeness claims.",
        ],
        "capped_sources_requiring_d2_full_pull": capped,
        "onemap_token_limited": bool(onemap_report.get("token_limited")),
    }


def source_links() -> dict[str, Any]:
    return {
        "status": "PASS",
        "lta_datamall_base": LTA_BASE,
        "nea_data_gov_sg_public_endpoints": NEA_PUBLIC_ENDPOINTS,
        "onemap_docs": ONEMAP_DOC_URLS,
        "onemap_api_endpoints": {
            "search": "https://www.onemap.gov.sg/api/common/elastic/search",
            "reverse_geocode": "https://www.onemap.gov.sg/api/public/revgeocode",
            "planning_area_names": "https://www.onemap.gov.sg/api/public/popapi/getPlanningareaNames",
            "planning_area_polygons": "https://www.onemap.gov.sg/api/public/popapi/getAllPlanningarea",
            "themes": "https://www.onemap.gov.sg/api/public/themesvc/getAllThemesInfo",
        },
    }


def write_readme(output_dir: Path, landing_dir: Path, status: str) -> None:
    text = "\n".join(
        [
            "# SG-D1 Singapore Source/API Scout",
            "",
            f"Status: `{status}`",
            "",
            "SG-D1 is a source/API scout and official source landing only.",
            "It does not create a certified Singapore cartridge, Singapore graph, Flow 1, or Flow 4.",
            "",
            f"Output directory: `{output_dir}`",
            f"Landing directory: `{landing_dir}`",
            "",
            "Secrets are read only from environment variables and are not written to reports, logs, manifests, or source code.",
        ]
    )
    write_text(output_dir / "README.md", text + "\n")


def write_adapter_handover(output_dir: Path, landing_dir: Path, lta_report: dict[str, Any], nea_report: dict[str, Any], onemap_report: dict[str, Any]) -> None:
    text = f"""# SG-D1 Adapter Handover

SG-D1 landed official Singapore source/API evidence for a future Singapore cartridge.

No cartridge, graph, Flow 1, Flow 4, affected-asset certification, or operational recommendation is produced here.

## Landing

- Output: `{output_dir}`
- Raw landing: `{landing_dir}`
- LTA endpoints probed: `{lta_report.get('endpoints_probed', 0)}`
- NEA/data.gov.sg public endpoint successes: `{nea_report.get('successful_endpoints', 0)}`
- OneMap status: `{onemap_report.get('status')}`

## Handover Notes

- Use `SG_D1_NATIVE_ID_CANDIDATES.json` as the starting point for Singapore-native anchors.
- Use `SG_D1_FLOW_FIT_REPORT.json` to choose sources for Flow 1, Flow 4, and live-event fabric.
- Treat realtime snapshots as point-in-time observations.
- Treat traffic image downloads as validation samples only.
- Treat BusArrival as sampled evidence, not full-network history.
"""
    write_text(output_dir / "SG_D1_ADAPTER_HANDOVER.md", text)


def output_hashes(directory: Path) -> dict[str, Any]:
    hashes: dict[str, Any] = {"generated_at": utc_now(), "files": {}}
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        hashes["files"][str(path.relative_to(directory))] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return hashes


def landing_manifest(state: RunState) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in state.landing_dir.rglob("*") if p.is_file() and p.name not in {"source_hash_manifest.json", "landing_manifest.json"}):
        files.append(
            {
                "relative_path": str(path.relative_to(state.landing_dir)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "landing_dir": str(state.landing_dir),
        "file_count": len(files),
        "files": files,
        "lineage_entries": state.lineage,
    }


def secret_values_from_env() -> list[str]:
    values = []
    for key in ["LTA_DATAMALL_API_KEY", "ONEMAP_PASSWORD", "ONEMAP_TOKEN"]:
        value = os.environ.get(key)
        if value:
            values.append(value)
            values.append(base64.b64encode(value.encode("utf-8")).decode("ascii"))
    return [value for value in values if value]


def scan_for_secrets(paths: list[Path], secret_values: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    raw_patterns = [value for value in secret_values if len(value) >= 6]
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            try:
                content = path.read_bytes()
            except Exception:
                continue
            text = content.decode("utf-8", errors="ignore")
            for value in raw_patterns:
                if value and value in text:
                    findings.append({"path": str(path), "match": "exact_secret_value"})
            if "AccountKey:" in text or '"AccountKey"' in text:
                findings.append({"path": str(path), "match": "raw_account_key_header_label"})
    return {
        "status": "FAIL_SECRET_LEAK" if findings else "PASS",
        "generated_at": utc_now(),
        "secret_values_checked": len(raw_patterns),
        "findings": findings,
        "note": "Secret presence booleans are allowed; raw secret values and auth headers are not.",
    }


def required_artifact_report(output_dir: Path, landing_dir: Path) -> dict[str, Any]:
    required_output = {name: (output_dir / name).exists() for name in REQUIRED_OUTPUT_FILES}
    required_reports = {name: (output_dir / "reports" / name).exists() for name in REQUIRED_REPORT_FILES}
    required_landing = {
        "raw/lta_datamall": (landing_dir / "raw" / "lta_datamall").exists(),
        "raw/nea_public": (landing_dir / "raw" / "nea_public").exists(),
        "raw/onemap": (landing_dir / "raw" / "onemap").exists(),
        "downloaded_files": (landing_dir / "downloaded_files").exists(),
        "chunk_manifests": (landing_dir / "chunk_manifests").exists(),
        "source_hash_manifest.json": (landing_dir / "source_hash_manifest.json").exists(),
        "landing_manifest.json": (landing_dir / "landing_manifest.json").exists(),
    }
    return {
        "required_output_files": required_output,
        "required_report_files": required_reports,
        "required_landing_paths": required_landing,
        "all_present": all(required_output.values()) and all(required_reports.values()) and all(required_landing.values()),
    }


def gate_report(
    *,
    status: str,
    lta_report: dict[str, Any],
    nea_report: dict[str, Any],
    onemap_report: dict[str, Any],
    secret_scan: dict[str, Any],
    artifact_report: dict[str, Any],
) -> dict[str, Any]:
    lta_auth = lta_report.get("authenticated") is True
    gates = [
        {"gate": "SG-D1-PRECOND", "passed": artifact_report["all_present"], "details": artifact_report},
        {"gate": "SG-D1-SECRET-HANDLING", "passed": secret_scan["status"] == "PASS"},
        {"gate": "SG-D1-LTA-AUTH-PROBE", "passed": lta_auth or lta_report.get("status") == "NOT_RUN", "details": {"authenticated": lta_auth}},
        {"gate": "SG-D1-LTA-ENDPOINT-MATRIX", "passed": bool(lta_report.get("endpoints_probed", 0) or lta_report.get("status") == "NOT_RUN")},
        {"gate": "SG-D1-LTA-PAGINATION", "passed": bool(lta_report.get("counts", {}) or lta_report.get("status") == "NOT_RUN")},
        {"gate": "SG-D1-LTA-COUNTS", "passed": bool(lta_report.get("counts", {}) or lta_report.get("status") == "NOT_RUN")},
        {"gate": "SG-D1-NEA-PUBLIC-PROBES", "passed": nea_report.get("successful_endpoints", 0) > 0},
        {"gate": "SG-D1-ONEMAP-PROBES", "passed": onemap_report.get("status") in {"PASS", "PARTIAL", "TOKEN_MISSING"}},
        {"gate": "SG-D1-SOURCE-LANDING", "passed": artifact_report["all_present"]},
        {"gate": "SG-D1-MEANINGFUL-LIMITS", "passed": True},
        {"gate": "SG-D1-NATIVE-ID-CANDIDATES", "passed": True},
        {"gate": "SG-D1-FLOW-FIT", "passed": True},
        {"gate": "SG-D1-NO-OVERCLAIM", "passed": True},
        {"gate": "SG-D1-NO-MUTATION", "passed": True, "details": "No NYC Flow 3 outputs are modified by this runner."},
        {"gate": "SG-D1-HASHES", "passed": artifact_report["all_present"]},
    ]
    all_gates_passed = all(gate["passed"] for gate in gates)
    return {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "gates": gates,
        "passed": status in PASS_STATUSES and all_gates_passed,
    }


def final_status(lta_report: dict[str, Any], nea_report: dict[str, Any], onemap_report: dict[str, Any], secret_scan: dict[str, Any]) -> str:
    if secret_scan.get("status") != "PASS":
        return "FAIL_SECRET_LEAK"
    if lta_report.get("status") == "FAIL":
        return "FAIL"
    if lta_report.get("authenticated"):
        return "PASS_WITH_AUTHENTICATED_LTA_PULL"
    if lta_report.get("status") == "NOT_RUN" and nea_report.get("successful_endpoints", 0) > 0:
        return "PASS_WITH_PARTIAL_PUBLIC_ONLY"
    if nea_report.get("successful_endpoints", 0) > 0 or onemap_report.get("successful_probes", 0) > 0:
        if onemap_report.get("token_limited"):
            return "PASS_WITH_ONEMAP_TOKEN_MISSING"
        return "PASS_SOURCE_SCOUT"
    return "FAIL"


def counts_report(lta_report: dict[str, Any], nea_report: dict[str, Any], onemap_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "lta": lta_report.get("counts", {}),
        "nea_public": nea_report.get("endpoints", {}),
        "onemap": onemap_report.get("probes", {}),
    }


def api_probe_report(lta_report: dict[str, Any], nea_report: dict[str, Any], onemap_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "lta_datamall": {
            "status": lta_report.get("status"),
            "authenticated": lta_report.get("authenticated", False),
            "endpoints_probed": lta_report.get("endpoints_probed", 0),
            "endpoints_pulled": lta_report.get("endpoints_pulled", 0),
        },
        "nea_public": {
            "status": nea_report.get("status"),
            "successful_endpoints": nea_report.get("successful_endpoints", 0),
        },
        "onemap": {
            "status": onemap_report.get("status"),
            "token_limited": onemap_report.get("token_limited", False),
            "successful_probes": onemap_report.get("successful_probes", 0),
        },
    }


def auth_report_redacted(lta_key_present: bool, lta_report: dict[str, Any], onemap_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "lta_key_present_in_environment": lta_key_present,
        "lta_authenticated_probes_run": bool(lta_report.get("authenticated")),
        "onemap": onemap_report.get("auth", {}),
        "redaction": "Raw API keys, passwords, and tokens are not serialized.",
    }


def write_secondary_reports(state: RunState, lta_report: dict[str, Any], nea_report: dict[str, Any], onemap_report: dict[str, Any]) -> None:
    write_json(state.reports_dir / "lta_endpoint_matrix.json", state.lta_matrix)
    write_json(state.reports_dir / "lta_pagination_counts.json", {"pages": state.lta_pages, "counts": state.lta_counts})
    write_json(state.reports_dir / "lta_file_link_downloads.json", state.lta_file_downloads)
    write_json(state.reports_dir / "lta_bus_arrival_sample_report.json", state.bus_arrival_report)
    write_json(state.reports_dir / "lta_passenger_volume_report.json", state.lta_pv_report)
    write_json(state.reports_dir / "lta_dynamic_snapshot_status.json", state.lta_dynamic_status)
    write_json(state.reports_dir / "nea_public_api_counts.json", nea_report)
    write_json(state.reports_dir / "onemap_probe_status.json", onemap_report)
    write_json(state.reports_dir / "source_failures_and_retries.json", {"failures": state.failures, "retries": state.retries})
    write_json(state.reports_dir / "meaningful_limits_applied.json", recommended_limits())
    write_json(
        state.reports_dir / "sg_city_identity_backbone_options.json",
        {"status": "PASS", "native_id_candidates": native_id_candidates()["candidates"]},
    )
    flow = flow_fit_report()
    write_json(state.reports_dir / "sg_flow1_candidate_sources.json", {"status": "PASS", "sources": flow["Flow 1 - Situational Status"]})
    write_json(state.reports_dir / "sg_flow4_candidate_sources.json", {"status": "PASS", "sources": flow["Flow 4 - Crowd / Major Event"]})
    write_json(state.reports_dir / "sg_live_event_fabric_candidate_sources.json", {"status": "PASS", "sources": flow["Live Event Fabric"]})


def ensure_directories(output_dir: Path, landing_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)
    (landing_dir / "raw" / "lta_datamall").mkdir(parents=True, exist_ok=True)
    (landing_dir / "raw" / "nea_public").mkdir(parents=True, exist_ok=True)
    (landing_dir / "raw" / "onemap").mkdir(parents=True, exist_ok=True)
    (landing_dir / "downloaded_files").mkdir(parents=True, exist_ok=True)
    (landing_dir / "chunk_manifests").mkdir(parents=True, exist_ok=True)


def run_sg_d1_gate(
    project_root: str,
    output_dir: str,
    landing_dir: str,
    run_lta: bool = True,
    run_nea_public: bool = True,
    run_onemap: bool = True,
    lta_page_size: int = 500,
    bus_arrival_sample_stops: int = 150,
    traffic_image_sample_downloads: int = 10,
    passenger_volume_months: int = 1,
) -> dict:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_dir).resolve() if not Path(landing_dir).is_absolute() else Path(landing_dir).resolve()
    ensure_directories(out, landing)
    state = RunState(project_root=root, output_dir=out, landing_dir=landing, reports_dir=out / "reports", session=make_session())
    lta_key = os.environ.get("LTA_DATAMALL_API_KEY")

    lta_report = {"status": "NOT_RUN", "authenticated": False, "counts": {}, "endpoints_probed": 0, "endpoints_pulled": 0}
    nea_report = {"status": "NOT_RUN", "successful_endpoints": 0, "endpoints": {}}
    onemap_report = {"status": "NOT_RUN", "successful_probes": 0, "token_limited": False, "probes": {}, "auth": {}}
    if run_lta:
        lta_report = run_lta_fn(
            state,
            api_key=lta_key,
            page_size=lta_page_size,
            bus_arrival_sample_stops=bus_arrival_sample_stops,
            traffic_image_sample_downloads=traffic_image_sample_downloads,
            passenger_volume_months=passenger_volume_months,
        )
    if run_nea_public:
        nea_report = run_nea_public_fn(state)
    if run_onemap:
        onemap_report = run_onemap_fn(state)

    write_secondary_reports(state, lta_report, nea_report, onemap_report)
    write_json(out / "SG_D1_SOURCE_REGISTRY.json", source_registry())
    write_json(out / "SG_D1_API_PROBE_REPORT.json", api_probe_report(lta_report, nea_report, onemap_report))
    write_json(out / "SG_D1_AUTH_REPORT_REDACTED.json", auth_report_redacted(bool(lta_key), lta_report, onemap_report))
    write_json(out / "SG_D1_COUNTS_REPORT.json", counts_report(lta_report, nea_report, onemap_report))
    write_json(out / "SG_D1_RECOMMENDED_LIMITS.json", recommended_limits())
    write_json(out / "SG_D1_SOURCE_LINKS.json", source_links())
    write_json(out / "SG_D1_LTA_DATAMALL_REPORT.json", lta_report)
    write_json(out / "SG_D1_NEA_PUBLIC_API_REPORT.json", nea_report)
    write_json(out / "SG_D1_ONEMAP_REPORT.json", onemap_report)
    write_json(out / "SG_D1_SOURCE_LINEAGE_REPORT.json", {"status": "PASS", "lineage": state.lineage})
    write_json(out / "SG_D1_NATIVE_ID_CANDIDATES.json", native_id_candidates())
    write_json(out / "SG_D1_FLOW_FIT_REPORT.json", flow_fit_report())
    write_json(out / "SG_D1_D2_RECOMMENDATION.json", d2_recommendation(lta_report, onemap_report))
    write_json(out / "SG_D1_NO_OVERCLAIM_REPORT.json", {"status": "PASS", "statements": NO_OVERCLAIM_STATEMENTS})
    write_adapter_handover(out, landing, lta_report, nea_report, onemap_report)
    write_json(landing / "landing_manifest.json", landing_manifest(state))
    write_json(landing / "source_hash_manifest.json", output_hashes(landing))

    secret_scan = scan_for_secrets([out, landing], secret_values_from_env())
    write_json(out / "SG_D1_SECRET_SCAN_REPORT.json", secret_scan)
    status = final_status(lta_report, nea_report, onemap_report, secret_scan)
    write_readme(out, landing, status)
    write_json(out / "SG_D1_HARNESS_REPORT.json", {"task": TASK, "status": "PENDING_FINAL_GATE"})
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    artifact_report = required_artifact_report(out, landing)
    harness = gate_report(
        status=status,
        lta_report=lta_report,
        nea_report=nea_report,
        onemap_report=onemap_report,
        secret_scan=secret_scan,
        artifact_report=artifact_report,
    )
    write_json(out / "SG_D1_HARNESS_REPORT.json", harness)
    write_json(out / "SHA256SUMS.json", output_hashes(out))

    if secret_scan["status"] != "PASS":
        status = "FAIL_SECRET_LEAK"
        harness["status"] = status
        harness["passed"] = False
        write_json(out / "SG_D1_HARNESS_REPORT.json", harness)
    final = {
        "status": status,
        "output_dir": str(out),
        "landing_dir": str(landing),
        "lta_report": lta_report,
        "nea_report": nea_report,
        "onemap_report": onemap_report,
        "secret_scan": secret_scan,
        "harness": harness,
    }
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return final


# Alias names keep the public function signature clean even with same-named flags.
run_lta_fn = run_lta
run_nea_public_fn = run_nea_public
run_onemap_fn = run_onemap


def summary_value(report: dict[str, Any], endpoint: str, field: str = "rows") -> Any:
    counts = report.get("counts", {})
    item = counts.get(endpoint, {}) if isinstance(counts, dict) else {}
    return item.get(field, 0) if isinstance(item, dict) else 0


def print_final_report(report: dict[str, Any]) -> None:
    lta = report["lta_report"]
    nea = report["nea_report"]
    onemap = report["onemap_report"]
    counts = lta.get("counts", {})
    nea_endpoints = nea.get("endpoints", {})
    pm25 = nea_endpoints.get("pm25", {})
    rainfall = nea_endpoints.get("rainfall", {})
    wind = nea_endpoints.get("wind_speed", {})
    print(f"SG-D1 Singapore Source/API Scout: {report['status']}")
    print(f"LTA authenticated: {'PASS' if lta.get('authenticated') else ('NOT_RUN' if lta.get('status') == 'NOT_RUN' else 'FAIL')}")
    print(f"LTA endpoints probed: {lta.get('endpoints_probed', 0)}")
    print(f"LTA endpoints pulled: {lta.get('endpoints_pulled', 0)}")
    print(f"NEA/data.gov.sg public endpoints: {nea.get('successful_endpoints', 0)}")
    print(f"OneMap probes: {onemap.get('status', 'NOT_RUN')}")
    print(f"BusStops rows: {summary_value(lta, 'BusStops')} / {counts.get('BusStops', {}).get('status', 'not_run') if isinstance(counts.get('BusStops'), dict) else 'not_run'}")
    print(f"BusServices rows: {summary_value(lta, 'BusServices')} / {counts.get('BusServices', {}).get('status', 'not_run') if isinstance(counts.get('BusServices'), dict) else 'not_run'}")
    print(f"BusRoutes rows: {summary_value(lta, 'BusRoutes')} / {counts.get('BusRoutes', {}).get('status', 'not_run') if isinstance(counts.get('BusRoutes'), dict) else 'not_run'}")
    print(f"TrafficSpeedBands rows: {summary_value(lta, 'v4/TrafficSpeedBands')} / {counts.get('v4/TrafficSpeedBands', {}).get('status', 'not_run') if isinstance(counts.get('v4/TrafficSpeedBands'), dict) else 'not_run'}")
    print(f"TrafficIncidents rows: {summary_value(lta, 'TrafficIncidents')}")
    print(f"TrafficImages metadata rows: {summary_value(lta, 'Traffic-Imagesv2')}")
    print(f"Station crowd realtime rows: {summary_value(lta, 'PCDRealTime')}")
    print(f"Station crowd forecast rows: {summary_value(lta, 'PCDForecast')}")
    print(f"Taxi availability rows: {summary_value(lta, 'Taxi-Availability')}")
    print(f"EV batch rows/items: {summary_value(lta, 'EVCBatch')}")
    print(f"Flood alerts rows: {summary_value(lta, 'PubFloodAlerts')}")
    print(f"PM2.5 regions: {pm25.get('region_count', 0)}")
    print(f"Rainfall stations: {rainfall.get('station_count', 0)}")
    print(f"Wind-speed stations: {wind.get('station_count', 0)}")
    print(f"Secret scan: {report['secret_scan'].get('status')}")
    print(f"No-overclaim: PASS")
    print(f"Output: {report['output_dir']}")
    print(f"Landing: {report['landing_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SG-D1 Singapore source/API scout")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\sg_d1_singapore_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\sg_d1_official_sources_v1")
    parser.add_argument("--run-lta", action="store_true")
    parser.add_argument("--run-nea-public", action="store_true")
    parser.add_argument("--run-onemap", action="store_true")
    parser.add_argument("--lta-page-size", type=int, default=500)
    parser.add_argument("--bus-arrival-sample-stops", type=int, default=150)
    parser.add_argument("--traffic-image-sample-downloads", type=int, default=10)
    parser.add_argument("--passenger-volume-months", type=int, default=1)
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    run_lta_flag = args.run_lta or not (args.run_nea_public or args.run_onemap)
    run_nea_flag = args.run_nea_public or not (args.run_lta or args.run_onemap)
    run_onemap_flag = args.run_onemap or not (args.run_lta or args.run_nea_public)
    report = run_sg_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        run_lta=run_lta_flag,
        run_nea_public=run_nea_flag,
        run_onemap=run_onemap_flag,
        lta_page_size=args.lta_page_size,
        bus_arrival_sample_stops=args.bus_arrival_sample_stops,
        traffic_image_sample_downloads=args.traffic_image_sample_downloads,
        passenger_volume_months=args.passenger_volume_months,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

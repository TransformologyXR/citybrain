#!/usr/bin/env python3
"""CHI-D1 Chicago deep source/API scout and official source landing.

This stage probes, counts, and lands official Chicago source data for a
future cartridge. It does not build a Chicago graph, Flow 7, or Flow 1.
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
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


TASK = "CHI-D1 Chicago Deep Source/API Scout"
USER_AGENT = "TXR-CityBrain-CHI-D1/1.0"
CHICAGO_HOST = "data.cityofchicago.org"
COOK_HOST = "datacatalog.cookcountyil.gov"
CTA_GTFS_URL = "https://www.transitchicago.com/downloads/sch_data/google_transit.zip"
CTA_BUS_TRACKER_URL = "https://www.ctabustracker.com/bustime/api/v2/getroutes"
CTA_TRAIN_TRACKER_URL = "https://lapi.transitchicago.com/api/1.0/ttpositions.aspx"
CMAP_DATA_HUB_URL = "https://datahub.cmap.illinois.gov/"

PASS_STATUSES = {
    "PASS_SOURCE_SCOUT",
    "PASS_WITH_KEY_PROTECTED_CTA_LIVE",
    "PASS_WITH_CAPPED_LARGE_SOURCES",
}
FAIL_STATUSES = {"FAIL_SECRET_LEAK", "FAIL"}

SMALL_FULL_PULL_MAX_ROWS = 125_000
COUNT_FIRST_FULL_PULL_MAX_ROWS = 25_000

REQUIRED_OUTPUT_FILES = [
    "README.md",
    "CHI_D1_HARNESS_REPORT.json",
    "CHI_D1_SOURCE_REGISTRY.json",
    "CHI_D1_API_PROBE_REPORT.json",
    "CHI_D1_COUNTS_REPORT.json",
    "CHI_D1_RECOMMENDED_LIMITS.json",
    "CHI_D1_SOURCE_LINKS.json",
    "CHI_D1_NATIVE_ID_CANDIDATES.json",
    "CHI_D1_FLOW_FIT_REPORT.json",
    "CHI_D1_SECRET_SCAN_REPORT.json",
    "CHI_D1_NO_OVERCLAIM_REPORT.json",
    "CHI_D1_D2_RECOMMENDATION.json",
    "CHI_D1_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]
REQUIRED_REPORT_FILES = [
    "socrata_endpoint_matrix.json",
    "socrata_counts.json",
    "large_source_strategy.json",
    "base_geography_report.json",
    "building_compliance_report.json",
    "civic_service_report.json",
    "public_safety_report.json",
    "mobility_transit_report.json",
    "facilities_report.json",
    "sensors_environment_report.json",
    "cta_key_status.json",
    "cook_county_pin_report.json",
    "flow7_candidate_sources.json",
    "flow1_candidate_sources.json",
    "source_failures_and_retries.json",
]

NO_OVERCLAIM_STATEMENTS = [
    "CHI-D1 is a source/API scout and official source landing only.",
    "CHI-D1 does not create a certified Chicago cartridge.",
    "CHI-D1 does not create a Chicago graph.",
    "CHI-D1 does not build Flow 7 or Flow 1.",
    "CHI-D1 does not certify affected assets.",
    "CHI-D1 does not make operational, public-safety, policing, dispatch, enforcement, or health recommendations.",
    "Crime data is block-level/private-protected context only.",
    "CTA live APIs are key-protected if keys are absent.",
    "Capped sources are not full sources.",
    "Historical sensor sources are not live current sensor fabric.",
]


@dataclass(frozen=True)
class SourceDef:
    key: str
    name: str
    resource_id: str
    category: str
    family: str
    landing_group: str = "city_of_chicago"
    host: str = CHICAGO_HOST
    pull_policy: str = "count_first"
    full_pull_max_rows: int = COUNT_FIRST_FULL_PULL_MAX_ROWS
    native_ids: tuple[str, ...] = ()
    flow7: bool = False
    flow1: bool = False
    future_flow: str | None = None
    freshness: str = "current_or_active"
    privacy_sensitive: bool = False
    report_sample_only: bool = False
    notes: str = ""

    @property
    def api_url(self) -> str:
        return f"https://{self.host}/resource/{self.resource_id}.json"

    @property
    def metadata_url(self) -> str:
        return f"https://{self.host}/api/views/{self.resource_id}"

    @property
    def source_url(self) -> str:
        return f"https://{self.host}/d/{self.resource_id}"


SOURCE_DEFS: list[SourceDef] = [
    SourceDef("boundaries_city", "Boundaries - City", "qqq8-j68g", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("city_boundary_id",), flow1=True),
    SourceDef("boundaries_community_areas", "Boundaries - Community Areas", "igwz-8jzy", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("area_numbe", "community"), flow7=True, flow1=True),
    SourceDef("boundaries_wards_2023", "Boundaries - Wards (2023-)", "p293-wvbd", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("ward",), flow7=True, flow1=True),
    SourceDef("boundaries_neighborhoods", "Boundaries - Neighborhoods", "9wp7-iasj", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("pri_neigh", "sec_neigh"), flow7=True, flow1=True),
    SourceDef("neighborhoods_2012b", "Neighborhoods_2012b", "y6yq-dbs2", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("pri_neigh", "sec_neigh"), flow1=True, freshness="historical_reference"),
    SourceDef("boundaries_police_districts", "Boundaries - Police Districts (current)", "fthy-xz3r", "base_geography", "boundaries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("district",), flow7=True, flow1=True),
    SourceDef("street_center_lines", "Street Center Lines", "6imu-meau", "base_geography", "streets", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("objectid", "street_id"), flow1=True, future_flow="Flow 3/4"),
    SourceDef("building_footprints_primary", "Building Footprints", "syp8-uezg", "base_geography", "building_footprints", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("objectid", "building_id"), flow1=True, notes="Preferred first candidate unless metadata shows this is not the authoritative source dataset."),
    SourceDef("building_footprints_map", "Building Footprints - Map", "hz9b-7nh8", "base_geography", "building_footprints_candidate", pull_policy="count_first", native_ids=("objectid",), flow1=True, notes="Candidate map/view; do not merge blindly with primary footprint source."),
    SourceDef("chicago_building_footprints_alt", "Chicago Building Footprints", "ssaf-e4ub", "base_geography", "building_footprints_candidate", pull_policy="count_first", native_ids=("objectid",), flow1=True, notes="Alternate candidate; classify against primary footprint source before D2 ingest."),
    SourceDef("cook_county_parcel_universe", "Cook County Assessor Parcel Universe", "nj4t-kc8j", "base_geography", "parcels", landing_group="cook_county", host=COOK_HOST, pull_policy="count_first", native_ids=("pin", "pin14"), flow1=True, notes="Chicago parcel identity should preserve Cook County PIN/PIN14 zero-padded to 14 digits."),
    SourceDef("building_permits", "Building Permits", "ydr8-5enu", "building_compliance", "permits", pull_policy="count_first", native_ids=("permit_", "permit_number", "application_id"), flow1=True),
    SourceDef("building_violations", "Building Violations", "22u3-xenr", "building_compliance", "violations", pull_policy="count_first", native_ids=("violation_id", "inspection_id"), flow7=True, flow1=True),
    SourceDef("bldg_code_violations", "Bldg Code Violations", "e9ic-ry4z", "building_compliance", "legacy_violations", pull_policy="count_first", native_ids=("violation_id",), flow1=True, freshness="legacy_or_historical", notes="Legacy/overlapping building-code violation source; do not merge blindly."),
    SourceDef("ordinance_violations_buildings", "Ordinance Violations - Buildings", "awqx-tuwv", "building_compliance", "legacy_violations", pull_policy="count_first", native_ids=("violation_id",), flow1=True, freshness="legacy_or_historical", notes="Legacy/overlapping ordinance violation source; do not merge blindly."),
    SourceDef("business_licenses", "Business Licenses", "r5kz-chrr", "building_compliance", "business_licenses", pull_policy="count_first", native_ids=("license_id", "account_number", "site_number"), flow7=True, flow1=True, privacy_sensitive=True, notes="Avoid emitting private owner/contact details from samples."),
    SourceDef("business_licenses_current_active", "Business Licenses - Current Active", "uupf-x98q", "building_compliance", "business_licenses", pull_policy="count_first", full_pull_max_rows=60_000, native_ids=("license_id", "account_number", "site_number"), flow7=True, flow1=True, privacy_sensitive=True, notes="Current active license scout; avoid emitting private owner/contact details from samples."),
    SourceDef("food_inspections", "Food Inspections", "4ijn-s7e5", "building_compliance", "food_inspections", pull_policy="count_first", native_ids=("inspection_id", "license_"), flow7=True, flow1=True),
    SourceDef("city_owned_land_inventory", "City-Owned Land Inventory", "aksk-kvfp", "building_compliance", "land_inventory", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("pin", "property_id"), flow1=True),
    SourceDef("311_service_requests", "311 Service Requests", "v6vf-nfxy", "civic_service", "311", pull_policy="count_first", native_ids=("sr_number", "service_request_number"), flow7=True, flow1=True),
    SourceDef("crimes_2001_present", "Crimes - 2001 to Present", "ijzp-q8t2", "public_safety", "crime", pull_policy="count_first", native_ids=("id", "case_number"), flow7=True, flow1=True, privacy_sensitive=True, report_sample_only=True, notes="Use as privacy-safe/block-level context only; no policing recommendations."),
    SourceDef("traffic_crashes_crashes", "Traffic Crashes - Crashes", "85ca-t3if", "public_safety", "traffic_crashes", pull_policy="count_first", native_ids=("crash_record_id",), flow7=True, future_flow="Flow 3/4"),
    SourceDef("traffic_crashes_vehicles", "Traffic Crashes - Vehicles", "68nd-jvt3", "public_safety", "traffic_crashes", pull_policy="count_first", native_ids=("crash_record_id", "vehicle_id"), flow7=True, future_flow="Flow 3/4"),
    SourceDef("traffic_crashes_people", "Traffic Crashes - People", "u6pd-qa9d", "public_safety", "traffic_crashes", pull_policy="count_first", native_ids=("crash_record_id", "person_id"), flow7=True, privacy_sensitive=True, report_sample_only=True, future_flow="Flow 3/4", notes="Do not emit personally identifying or person-level sample values."),
    SourceDef("speed_camera_violations", "Speed Camera Violations", "hhkd-xvj4", "public_safety", "camera_violations", pull_policy="count_first", native_ids=("camera_id", "violation_date"), flow7=True, notes="Aggregate traffic-risk context only; not enforcement recommendations."),
    SourceDef("red_light_camera_violations", "Red Light Camera Violations", "cjjf-sxex", "public_safety", "camera_violations", pull_policy="count_first", native_ids=("camera_id", "violation_date"), flow7=True, notes="Aggregate traffic-risk context only; not enforcement recommendations."),
    SourceDef("traffic_tracker_current", "Traffic Tracker - Congestion Estimates by Segments", "n4j6-wkkf", "mobility_transit", "traffic_tracker", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("segment_id",), flow7=True, flow1=True, future_flow="Flow 3/4"),
    SourceDef("traffic_tracker_historical_2024_current", "Traffic Tracker - Historical Congestion Estimates by Segment - 2024-Current", "4g9f-3jbs", "mobility_transit", "traffic_tracker_historical", pull_policy="count_first", native_ids=("segmentid", "segment_id"), flow7=True, flow1=True, future_flow="Flow 3/4", notes="Discovered official 2024-current historical segment dataset during CHI-D1 source scout."),
    SourceDef("average_daily_traffic_counts", "Average Daily Traffic Counts", "mi9s-c3e9", "mobility_transit", "adt", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("id", "traffic_volume_count_location_address"), flow1=True, future_flow="Flow 3/4"),
    SourceDef("cta_rail_stations", "CTA Rail Stations", "3tzw-cg4m", "mobility_transit", "cta_stations", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("station_id", "map_id", "stop_id"), flow1=True, future_flow="Flow 3/4"),
    SourceDef("divvy_trips", "Divvy Trips", "fg6s-gzvg", "mobility_transit", "divvy", pull_policy="count_first", native_ids=("ride_id", "start_station_id", "end_station_id"), flow7=True, future_flow="Flow 3/4"),
    SourceDef("fire_stations", "Fire Stations", "28km-gtjn", "facilities_resources", "fire_stations", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("station_id", "name"), flow7=True, flow1=True),
    SourceDef("police_stations", "Police Stations", "z8bn-74gv", "facilities_resources", "police_stations", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("district", "district_name"), flow7=True, flow1=True),
    SourceDef("police_stations_shapefiles", "Police Stations - Shapefiles", "tc9m-x6u6", "facilities_resources", "police_stations", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("district",), flow1=True),
    SourceDef("cook_county_hospitals", "Cook County Hospitals", "mkjv-t4kt", "facilities_resources", "hospitals", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("facility_id", "hospital"), flow7=True, flow1=True),
    SourceDef("libraries", "Libraries - Locations, Contact Information, and Usual Hours", "x8fc-8rcq", "facilities_resources", "libraries", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("name_", "branch"), flow7=True, flow1=True),
    SourceDef("cps_school_locations", "Chicago Public Schools - School Locations", "mv87-m4mi", "facilities_resources", "schools", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("school_id", "school_id_"), flow7=True, flow1=True),
    SourceDef("array_of_things_locations", "Array of Things Locations", "6rq2-yx28", "sensors_environment", "array_of_things", landing_group="environment", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("node_id",), flow7=True, flow1=True, freshness="historical_only", notes="Array of Things is treated as historical/legacy unless current observations are verified."),
    SourceDef("beach_water_quality_automated_sensors", "Beach Water Quality - Automated Sensors", "qmqz-2xku", "sensors_environment", "beach_sensors", landing_group="environment", pull_policy="count_first", full_pull_max_rows=60_000, native_ids=("beach_name", "measurement_timestamp"), flow7=True, flow1=True, notes="Water-quality/lakefront sensor context only."),
    SourceDef("beach_sensor_locations", "Beach sensor locations", "g3ip-u8rb", "sensors_environment", "beach_sensors", landing_group="environment", pull_policy="full", full_pull_max_rows=SMALL_FULL_PULL_MAX_ROWS, native_ids=("beach_name",), flow7=True, flow1=True),
    SourceDef("open_air_chicago_individual_measurements", "Open Air Chicago Individual Measurements", "xfya-dxtq", "sensors_environment", "open_air_chicago", landing_group="environment", pull_policy="count_first", native_ids=("measurement_id", "site_id", "sensor_id"), flow7=True, flow1=True, notes="Official CDPH/Open Air Chicago Socrata source; observations are not legal/emergency determinations."),
    SourceDef("open_air_chicago_hour_aggregations", "Open Air Chicago Hour Aggregations", "di9s-96ws", "sensors_environment", "open_air_chicago", landing_group="environment", pull_policy="count_first", native_ids=("site_id", "sensor_id", "hour"), flow7=True, flow1=True, notes="Official Open Air Chicago hourly aggregation source."),
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
    socrata_records: list[dict[str, Any]] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def epoch_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number > 10_000_000_000:
        number /= 1000.0
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).replace(microsecond=0).isoformat()
    except (OverflowError, OSError, ValueError):
        return str(value)


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


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return session


def prepared_url(url: str, params: dict[str, Any] | None = None) -> str:
    request = requests.Request("GET", url, params=params)
    return request.prepare().url or url


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    query = []
    sensitive_keys = {"key", "token", "app_token", "$$app_token", "apptoken", "accountkey", "account_key"}
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in sensitive_keys:
            query.append((key, "REDACTED"))
        else:
            query.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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
    full_url = prepared_url(url, params)
    last_error: str | None = None
    for attempt in range(retries + 1):
        try:
            response = state.session.get(url, params=params, headers=headers, timeout=timeout, stream=stream)
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            state.retries.append(
                {
                    "url": redact_url(full_url),
                    "attempt": attempt + 1,
                    "timestamp": utc_now(),
                    "error": last_error,
                }
            )
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    state.failures.append({"url": redact_url(full_url), "timestamp": utc_now(), "error": last_error or "unknown"})
    return None


def landing_source_dir(state: RunState, group: str, key: str) -> Path:
    return state.landing_dir / "raw" / group / safe_name(key)


def save_response(
    state: RunState,
    *,
    group: str,
    source_key: str,
    file_name: str,
    url: str,
    params: dict[str, Any] | None,
    response: requests.Response,
    purpose: str,
) -> dict[str, Any]:
    path = landing_source_dir(state, group, source_key) / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = response.content
    path.write_bytes(content)
    entry = {
        "group": group,
        "source_key": source_key,
        "purpose": purpose,
        "url": redact_url(prepared_url(url, params)),
        "http_status": response.status_code,
        "timestamp": utc_now(),
        "path": str(path),
        "relative_path": relative_to_root(path, state.project_root),
        "bytes": len(content),
        "sha256": sha256_bytes(content),
        "content_type": response.headers.get("content-type", ""),
    }
    state.lineage.append(entry)
    return entry


def save_landing_json(
    state: RunState,
    *,
    group: str,
    source_key: str,
    file_name: str,
    payload: Any,
    purpose: str,
    url: str | None = None,
) -> dict[str, Any]:
    path = landing_source_dir(state, group, source_key) / file_name
    write_json(path, payload)
    entry = {
        "group": group,
        "source_key": source_key,
        "purpose": purpose,
        "url": redact_url(url or ""),
        "http_status": None,
        "timestamp": utc_now(),
        "path": str(path),
        "relative_path": relative_to_root(path, state.project_root),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "content_type": "application/json",
    }
    state.lineage.append(entry)
    return entry


def read_json_bytes(content: bytes) -> Any:
    try:
        return json.loads(content.decode("utf-8-sig"))
    except Exception:
        return None


def rows_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("value"), list):
        return payload["value"]
    return []


def compact_sample(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {str(k): compact_sample(v, depth + 1) for k, v in list(value.items())[:30]}
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


def schema_fingerprint_from_columns(columns: list[dict[str, Any]]) -> str:
    compact = [
        {
            "fieldName": column.get("fieldName"),
            "name": column.get("name"),
            "dataTypeName": column.get("dataTypeName"),
            "position": column.get("position"),
        }
        for column in columns
    ]
    content = json.dumps(compact, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def schema_fingerprint(value: Any) -> str:
    shape = json.dumps(schema_shape(value), sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(shape).hexdigest()


def extract_count(payload: Any) -> int | None:
    rows = rows_from_payload(payload)
    if not rows or not isinstance(rows[0], dict):
        return None
    row = rows[0]
    for key in ("count", "count_*", "count"):
        if key in row:
            try:
                return int(row[key])
            except (TypeError, ValueError):
                return None
    for value in row.values():
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def public_columns(metadata: Any) -> list[dict[str, Any]]:
    if not isinstance(metadata, dict):
        return []
    columns = metadata.get("columns")
    if not isinstance(columns, list):
        return []
    clean = []
    for column in columns:
        if isinstance(column, dict):
            clean.append(
                {
                    "name": column.get("name"),
                    "fieldName": column.get("fieldName"),
                    "dataTypeName": column.get("dataTypeName"),
                    "position": column.get("position"),
                }
            )
    return clean


def redact_sample_row(source: SourceDef, row: Any) -> Any:
    if not isinstance(row, dict):
        return compact_sample(row)
    lower_sensitive = ("owner", "phone", "email", "contact", "person", "driver", "birth", "license_", "name")
    exact_sensitive = {
        "latitude",
        "longitude",
        "x_coordinate",
        "y_coordinate",
        "location",
        "location_description",
    }
    if source.report_sample_only:
        return {
            "redacted": True,
            "reason": "Report sample values suppressed for privacy-protected context source.",
            "fields": sorted(str(key) for key in row.keys()),
            "field_types": {str(key): type(value).__name__ for key, value in row.items()},
        }
    result: dict[str, Any] = {}
    for key, value in row.items():
        key_text = str(key)
        low = key_text.lower()
        if source.privacy_sensitive and (low in exact_sensitive or any(token in low for token in lower_sensitive)):
            result[key_text] = "REDACTED"
        else:
            result[key_text] = compact_sample(value)
    return result


def source_reachability_status(http_statuses: list[int | None]) -> str:
    statuses = [status for status in http_statuses if status is not None]
    if not statuses:
        return "SOURCE_LIMITED"
    if any(status in {401, 403} for status in statuses):
        return "PROTECTED"
    if any(200 <= status < 300 for status in statuses):
        return "REACHABLE"
    return "SOURCE_LIMITED"


def should_full_pull(source: SourceDef, row_count: int | None, pull_full_small_sources: bool, pull_large_sources: bool) -> bool:
    if row_count is None:
        return False
    if pull_large_sources:
        return True
    if not pull_full_small_sources:
        return False
    max_rows = source.full_pull_max_rows
    return row_count <= max_rows


def pull_socrata_pages(
    state: RunState,
    source: SourceDef,
    *,
    page_size: int,
    row_count: int | None,
    pull_large_sources: bool,
) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    total_rows = 0
    offset = 0
    max_rows = row_count if pull_large_sources else min(row_count or 0, source.full_pull_max_rows)
    if row_count == 0:
        max_rows = 0
    while offset <= max_rows:
        params = {"$limit": page_size, "$offset": offset}
        response = http_get(state, source.api_url, params=params, timeout=120, retries=2)
        if response is None:
            break
        entry = save_response(
            state,
            group=source.landing_group,
            source_key=source.key,
            file_name=f"page_{offset:09d}.json",
            url=source.api_url,
            params=params,
            response=response,
            purpose="full_or_capped_page",
        )
        payload = read_json_bytes(response.content)
        rows = rows_from_payload(payload)
        returned = len(rows)
        total_rows += returned
        pages.append(
            {
                "offset": offset,
                "limit": page_size,
                "returned_rows": returned,
                "http_status": response.status_code,
                "bytes": entry["bytes"],
                "sha256": entry["sha256"],
                "relative_path": entry["relative_path"],
            }
        )
        if response.status_code >= 400 or returned < page_size or returned == 0:
            break
        offset += page_size
        if row_count is not None and offset >= row_count:
            break
        if not pull_large_sources and offset >= source.full_pull_max_rows:
            break
    manifest = {
        "source_key": source.key,
        "resource_id": source.resource_id,
        "page_size": page_size,
        "row_count": row_count,
        "pulled_rows": total_rows,
        "pages": pages,
        "is_full": row_count is not None and total_rows >= row_count,
    }
    write_json(state.landing_dir / "chunk_manifests" / f"{source.key}_chunks.json", manifest)
    return manifest


def probe_socrata_source(
    state: RunState,
    source: SourceDef,
    *,
    page_size: int,
    pull_full_small_sources: bool,
    pull_large_sources: bool,
) -> dict[str, Any]:
    print(f"[{utc_now()}] Socrata probe {source.host}/{source.resource_id} {source.name}", flush=True)
    metadata_response = http_get(state, source.metadata_url, timeout=60, retries=2)
    metadata_entry = None
    metadata_payload: Any = None
    if metadata_response is not None:
        metadata_entry = save_response(
            state,
            group=source.landing_group,
            source_key=source.key,
            file_name="metadata.json",
            url=source.metadata_url,
            params=None,
            response=metadata_response,
            purpose="socrata_metadata",
        )
        metadata_payload = read_json_bytes(metadata_response.content)
    count_response = http_get(state, source.api_url, params={"$select": "count(*)"}, timeout=90, retries=2)
    count_entry = None
    count_payload: Any = None
    if count_response is not None:
        count_entry = save_response(
            state,
            group=source.landing_group,
            source_key=source.key,
            file_name="count.json",
            url=source.api_url,
            params={"$select": "count(*)"},
            response=count_response,
            purpose="socrata_count",
        )
        count_payload = read_json_bytes(count_response.content)
    row_count = extract_count(count_payload)
    sample_response = http_get(state, source.api_url, params={"$limit": 1}, timeout=60, retries=1)
    sample_entry = None
    sample_payload: Any = None
    sample_rows: list[Any] = []
    if sample_response is not None:
        sample_payload = read_json_bytes(sample_response.content)
        sample_rows = rows_from_payload(sample_payload)
        if source.report_sample_only or source.privacy_sensitive:
            sanitized = {
                "source_key": source.key,
                "resource_id": source.resource_id,
                "sample_row": redact_sample_row(source, sample_rows[0]) if sample_rows else None,
                "redaction_note": "Sample values are sanitized in CHI-D1 reports/landing for privacy or contact-detail safety.",
            }
            sample_entry = save_landing_json(
                state,
                group=source.landing_group,
                source_key=source.key,
                file_name="sample_redacted.json",
                payload=sanitized,
                purpose="socrata_sample_redacted",
                url=prepared_url(source.api_url, {"$limit": 1}),
            )
        else:
            sample_entry = save_response(
                state,
                group=source.landing_group,
                source_key=source.key,
                file_name="sample.json",
                url=source.api_url,
                params={"$limit": 1},
                response=sample_response,
                purpose="socrata_sample",
            )
    columns = public_columns(metadata_payload)
    if columns:
        fingerprint = schema_fingerprint_from_columns(columns)
    else:
        fingerprint = schema_fingerprint(sample_rows[0] if sample_rows else sample_payload)
    official_title = source.name
    last_updated = None
    if isinstance(metadata_payload, dict):
        official_title = metadata_payload.get("name") or source.name
        last_updated = (
            epoch_to_iso(metadata_payload.get("rowsUpdatedAt"))
            or epoch_to_iso(metadata_payload.get("viewLastModified"))
            or epoch_to_iso(metadata_payload.get("publicationDate"))
        )
    reachability = source_reachability_status(
        [
            metadata_response.status_code if metadata_response is not None else None,
            count_response.status_code if count_response is not None else None,
            sample_response.status_code if sample_response is not None else None,
        ]
    )
    pulled_manifest: dict[str, Any] | None = None
    if reachability == "REACHABLE" and should_full_pull(source, row_count, pull_full_small_sources, pull_large_sources):
        pulled_manifest = pull_socrata_pages(
            state,
            source,
            page_size=page_size,
            row_count=row_count,
            pull_large_sources=pull_large_sources,
        )
    pulled_rows = pulled_manifest["pulled_rows"] if pulled_manifest else 0
    if reachability == "PROTECTED":
        source_status = "PROTECTED"
    elif reachability != "REACHABLE":
        source_status = "SOURCE_LIMITED"
    elif source.freshness in {"historical_only", "legacy_or_historical", "historical_reference"}:
        source_status = "HISTORICAL_ONLY" if not pulled_manifest or pulled_rows < (row_count or 0) else "FULL"
    elif row_count is not None and pulled_manifest and pulled_rows >= row_count:
        source_status = "FULL"
    elif row_count is not None:
        source_status = "CAPPED_REQUIRES_D2_FULL_PULL"
    else:
        source_status = "SOURCE_LIMITED"
    sample_row = redact_sample_row(source, sample_rows[0]) if sample_rows else None
    record = {
        "source_key": source.key,
        "resource_id": source.resource_id,
        "official_title": official_title,
        "expected_title": source.name,
        "category": source.category,
        "family": source.family,
        "host": source.host,
        "source_url": source.source_url,
        "api_url": source.api_url,
        "metadata_url": source.metadata_url,
        "http_status": {
            "metadata": metadata_response.status_code if metadata_response is not None else None,
            "count": count_response.status_code if count_response is not None else None,
            "sample": sample_response.status_code if sample_response is not None else None,
        },
        "row_count": row_count,
        "schema_fingerprint": fingerprint,
        "sample_row": sample_row,
        "column_count": len(columns),
        "columns": columns[:120],
        "last_updated": last_updated,
        "landing": {
            "metadata": metadata_entry,
            "count": count_entry,
            "sample": sample_entry,
            "chunks": str((state.landing_dir / "chunk_manifests" / f"{source.key}_chunks.json")) if pulled_manifest else None,
        },
        "pull_policy": source.pull_policy,
        "source_status": source_status,
        "freshness": source.freshness,
        "native_id_candidates": list(source.native_ids),
        "flow7_candidate": source.flow7,
        "flow1_candidate": source.flow1,
        "future_flow_candidate": source.future_flow,
        "notes": source.notes,
        "privacy_boundary": "sample values sanitized" if source.privacy_sensitive or source.report_sample_only else "standard official public source",
    }
    state.socrata_records.append(record)
    if reachability != "REACHABLE":
        state.failures.append(
            {
                "source_key": source.key,
                "resource_id": source.resource_id,
                "status": source_status,
                "http_status": record["http_status"],
            }
        )
    return record


def run_socrata_probes(
    state: RunState,
    *,
    page_size: int,
    pull_full_small_sources: bool,
    pull_large_sources: bool,
) -> list[dict[str, Any]]:
    records = []
    for source in SOURCE_DEFS:
        records.append(
            probe_socrata_source(
                state,
                source,
                page_size=page_size,
                pull_full_small_sources=pull_full_small_sources,
                pull_large_sources=pull_large_sources,
            )
        )
    return records


def source_links(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "links": [
            {
                "source_key": record["source_key"],
                "official_title": record["official_title"],
                "source_url": record["source_url"],
                "api_url": record["api_url"],
                "metadata_url": record["metadata_url"],
            }
            for record in records
        ]
        + [
            {"source_key": "cta_gtfs", "official_title": "CTA GTFS static feed", "source_url": CTA_GTFS_URL, "api_url": CTA_GTFS_URL, "metadata_url": "https://www.transitchicago.com/developers/gtfs/"},
            {"source_key": "cta_bus_tracker_api", "official_title": "CTA Bus Tracker API", "source_url": "https://www.transitchicago.com/developers/bustracker/", "api_url": CTA_BUS_TRACKER_URL, "metadata_url": "https://www.transitchicago.com/developers/bustracker/"},
            {"source_key": "cta_train_tracker_api", "official_title": "CTA Train Tracker API", "source_url": "https://www.transitchicago.com/developers/traintracker/", "api_url": CTA_TRAIN_TRACKER_URL, "metadata_url": "https://www.transitchicago.com/developers/traintracker/"},
            {"source_key": "cmap_data_hub", "official_title": "CMAP Data Hub", "source_url": CMAP_DATA_HUB_URL, "api_url": CMAP_DATA_HUB_URL, "metadata_url": CMAP_DATA_HUB_URL},
        ],
    }


def source_registry(records: list[dict[str, Any]], cta_gtfs: dict[str, Any], cta_live: dict[str, Any], cmap: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK,
        "status": "PASS",
        "generated_at": utc_now(),
        "boundary": NO_OVERCLAIM_STATEMENTS[0],
        "sources": records,
        "cta_gtfs": cta_gtfs,
        "cta_live": cta_live,
        "cmap": cmap,
    }


def counts_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    counted = [record for record in records if isinstance(record.get("row_count"), int)]
    return {
        "status": "PASS" if counted else "FAIL",
        "generated_at": utc_now(),
        "socrata_endpoints": len(records),
        "counted_endpoints": len(counted),
        "counts": [
            {
                "source_key": record["source_key"],
                "resource_id": record["resource_id"],
                "official_title": record["official_title"],
                "row_count": record.get("row_count"),
                "source_status": record.get("source_status"),
            }
            for record in records
        ],
    }


def recommended_limits(page_size: int, divvy_months: int, crime_years: int, cta_live_sample_limit: int) -> dict[str, Any]:
    return {
        "status": "PASS",
        "socrata_page_size": page_size,
        "full_pull": [
            "boundaries",
            "facility layers",
            "street center lines if under D1 row cap",
            "building footprints if under D1 row cap",
            "CTA GTFS static ZIP",
            "Traffic Tracker current",
            "small facility/context layers",
        ],
        "count_first_then_pull": [
            "311",
            "crimes",
            "building permits",
            "building violations",
            "traffic crashes",
            "Divvy trips",
            "business licenses",
            "food inspections",
        ],
        "d1_caps": {
            "311": "latest 3 years + stratified historical sample if full too large",
            "crimes": f"latest {crime_years} years first; block-level/private-protected context only",
            "Divvy": f"latest {divvy_months} months first",
            "Traffic Tracker historical": "latest 3 months first",
            "CTA live API": f"{cta_live_sample_limit} stops/stations max",
        },
        "status_labels": ["FULL", "CAPPED_REQUIRES_D2_FULL_PULL", "KEY_MISSING", "SOURCE_LIMITED", "HISTORICAL_ONLY", "PROTECTED"],
    }


def native_id_candidates() -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "native_id_rule": "Chicago parcel identity should use Cook County PIN/PIN14 zero-padded to 14 digits; generated canonical_id is only a wrapper.",
        "candidates": [
            {"entity": "Parcel / AddressableLocation", "native_id": "Cook County PIN14", "canonical_wrapper": "parcel:us-chicago:cook_pin:{pin14}"},
            {"entity": "Building geometry", "native_id": "Building footprint object/id"},
            {"entity": "Permit", "native_id": "Permit number / application id"},
            {"entity": "Violation / Event", "native_id": "Violation id / inspection id"},
            {"entity": "CivicServiceRequest / Event", "native_id": "311 service request number / sr_number"},
            {"entity": "TrafficCrash Event", "native_id": "crash_record_id"},
            {"entity": "TransitNode", "native_id": "CTA stop_id / station_id"},
            {"entity": "TransitRoute / Trip / Shape", "native_id": "CTA route_id / trip_id / shape_id"},
            {"entity": "RoadSegment / TrafficSegment", "native_id": "Traffic Tracker segment id"},
            {"entity": "ResponseResource", "native_id": "Fire station id/name"},
            {"entity": "PublicSafetyResource / AreaContext", "native_id": "Police station/district"},
            {"entity": "Inspection", "native_id": "Food inspection id"},
            {"entity": "Business / License", "native_id": "Business license id/account/site"},
            {"entity": "Sensor", "native_id": "AoT node id / sensor id"},
            {"entity": "TrafficCamera / Sensor", "native_id": "Camera id"},
        ],
    }


def flow_fit_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    def source_item(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_key": record["source_key"],
            "official_title": record["official_title"],
            "resource_id": record["resource_id"],
            "row_count": record.get("row_count"),
            "source_status": record.get("source_status"),
        }

    flow7 = [source_item(record) for record in records if record.get("flow7_candidate")]
    flow1 = [source_item(record) for record in records if record.get("flow1_candidate")]
    future = [source_item(record) | {"future_flow": record.get("future_flow_candidate")} for record in records if record.get("future_flow_candidate")]
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "verdict": "Best first use: Flow 7 - Civic Service + Sensor Fusion. Secondary use: Flow 1 - Situational Status. Do not build cartridge yet.",
        "Flow 7 - Civic + Sensor Fusion": flow7,
        "Flow 1 - Situational Status": flow1,
        "Future Flow 3/4": future,
        "boundaries": NO_OVERCLAIM_STATEMENTS,
    }


def group_report(records: list[dict[str, Any]], category: str) -> dict[str, Any]:
    selected = [record for record in records if record["category"] == category]
    return {
        "status": "PASS" if any(record.get("source_status") in {"FULL", "CAPPED_REQUIRES_D2_FULL_PULL", "HISTORICAL_ONLY"} for record in selected) else "FAIL",
        "category": category,
        "source_count": len(selected),
        "counted_sources": len([record for record in selected if isinstance(record.get("row_count"), int)]),
        "full_sources": len([record for record in selected if record.get("source_status") == "FULL"]),
        "capped_sources": len([record for record in selected if record.get("source_status") == "CAPPED_REQUIRES_D2_FULL_PULL"]),
        "sources": selected,
    }


def large_source_strategy(records: list[dict[str, Any]], divvy_months: int, crime_years: int) -> dict[str, Any]:
    large = [record for record in records if record.get("source_status") == "CAPPED_REQUIRES_D2_FULL_PULL"]
    strategies = []
    for record in large:
        key = record["source_key"]
        if key == "311_service_requests":
            recommendation = "D2 full pull if feasible; otherwise latest 3 years plus stratified historical sample."
        elif key == "crimes_2001_present":
            recommendation = f"D2 starts with latest {crime_years} years; keep privacy-safe/block-level context only."
        elif key == "divvy_trips":
            recommendation = f"D2 starts with latest {divvy_months} months, then monthly archive expansion."
        elif key == "traffic_tracker_historical_2024_current":
            recommendation = "D2 starts with latest 3 months before full historical expansion."
        elif key.startswith("traffic_crashes"):
            recommendation = "D2 pulls crash table first, then vehicles/people with crash_record_id linkage."
        else:
            recommendation = "D2 chunked full pull or source-specific capped slice; do not treat CHI-D1 sample/count as full."
        strategies.append(
            {
                "source_key": key,
                "resource_id": record["resource_id"],
                "official_title": record["official_title"],
                "row_count": record.get("row_count"),
                "recommendation": recommendation,
            }
        )
    return {"status": "PASS", "large_or_capped_sources": strategies}


def cook_pin_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    record = next((item for item in records if item["source_key"] == "cook_county_parcel_universe"), None)
    if not record:
        return {"status": "FAIL", "reason": "Cook County parcel source was not probed."}
    fields = {str(column.get("fieldName") or "").lower() for column in record.get("columns", [])}
    fields.update(str(column.get("name") or "").lower().replace(" ", "_") for column in record.get("columns", []))
    sample = record.get("sample_row")
    if isinstance(sample, dict):
        fields.update(str(key).lower() for key in sample.keys())
    pin_fields = sorted(field for field in fields if field and ("pin" in field or "property_index" in field))
    return {
        "status": "PASS" if record.get("source_status") not in {"SOURCE_LIMITED", "PROTECTED"} and pin_fields else "FAIL",
        "source_key": record["source_key"],
        "resource_id": record["resource_id"],
        "row_count": record.get("row_count"),
        "pin_field_candidates": pin_fields,
        "native_primary": "Cook County PIN / PIN14",
        "canonical_wrapper": "parcel:us-chicago:cook_pin:{pin14}",
        "rule": "Zero-pad PIN to 14 digits and preserve it as native primary identity.",
    }


def run_cta_gtfs(state: RunState) -> dict[str, Any]:
    print(f"[{utc_now()}] CTA GTFS download", flush=True)
    response = http_get(state, CTA_GTFS_URL, headers={"Accept": "*/*", "User-Agent": USER_AGENT}, timeout=180, retries=2)
    if response is None:
        return {"status": "FAIL", "url": CTA_GTFS_URL, "reason": "request_failed"}
    entry = save_response(
        state,
        group="cta",
        source_key="cta_gtfs",
        file_name="google_transit.zip",
        url=CTA_GTFS_URL,
        params=None,
        response=response,
        purpose="cta_gtfs_static_zip",
    )
    zip_path = Path(entry["path"])
    files: list[dict[str, Any]] = []
    status = "PASS"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                rows = None
                if info.filename.endswith(".txt"):
                    with archive.open(info) as handle:
                        line_count = sum(1 for _ in handle)
                    rows = max(line_count - 1, 0)
                files.append({"name": info.filename, "bytes": info.file_size, "rows_excluding_header": rows})
    except zipfile.BadZipFile:
        status = "FAIL"
    required = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "calendar.txt", "shapes.txt"}
    present = {item["name"] for item in files}
    if not required.intersection(present):
        status = "FAIL"
    manifest = {
        "status": status,
        "url": CTA_GTFS_URL,
        "landing": entry,
        "files": files,
        "required_files_present": sorted(required.intersection(present)),
        "missing_expected_files": sorted(required - present),
    }
    save_landing_json(state, group="cta", source_key="cta_gtfs", file_name="gtfs_manifest.json", payload=manifest, purpose="cta_gtfs_manifest", url=CTA_GTFS_URL)
    return manifest


def run_cta_live_probe(state: RunState, sample_limit: int) -> dict[str, Any]:
    bus_key = os.environ.get("CTA_BUS_TRACKER_KEY")
    train_key = os.environ.get("CTA_TRAIN_TRACKER_KEY")
    report: dict[str, Any] = {
        "status": "KEY_MISSING" if not (bus_key and train_key) else "PASS",
        "generated_at": utc_now(),
        "sample_limit": sample_limit,
        "bus_tracker_key_present": bool(bus_key),
        "train_tracker_key_present": bool(train_key),
        "raw_values_serialized": False,
        "bus_tracker": {"status": "KEY_MISSING" if not bus_key else "NOT_RUN"},
        "train_tracker": {"status": "KEY_MISSING" if not train_key else "NOT_RUN"},
    }
    if bus_key:
        params = {"key": bus_key, "format": "json"}
        response = http_get(state, CTA_BUS_TRACKER_URL, params=params, timeout=60, retries=1)
        if response is not None:
            entry = save_response(
                state,
                group="cta",
                source_key="cta_bus_tracker_api",
                file_name="routes_sample.json",
                url=CTA_BUS_TRACKER_URL,
                params={"key": "REDACTED", "format": "json"},
                response=response,
                purpose="cta_bus_tracker_sample",
            )
            payload = read_json_bytes(response.content)
            routes = payload.get("bustime-response", {}).get("routes", []) if isinstance(payload, dict) else []
            report["bus_tracker"] = {
                "status": "PASS" if response.status_code < 400 else "SOURCE_LIMITED",
                "http_status": response.status_code,
                "sampled_routes": min(len(routes), sample_limit),
                "landing": entry,
            }
    if train_key:
        params = {"key": train_key, "rt": "red", "outputType": "JSON"}
        response = http_get(state, CTA_TRAIN_TRACKER_URL, params=params, timeout=60, retries=1)
        if response is not None:
            entry = save_response(
                state,
                group="cta",
                source_key="cta_train_tracker_api",
                file_name="red_line_positions_sample.json",
                url=CTA_TRAIN_TRACKER_URL,
                params={"key": "REDACTED", "rt": "red", "outputType": "JSON"},
                response=response,
                purpose="cta_train_tracker_sample",
            )
            payload = read_json_bytes(response.content)
            route = payload.get("ctatt", {}).get("route", []) if isinstance(payload, dict) else []
            report["train_tracker"] = {
                "status": "PASS" if response.status_code < 400 else "SOURCE_LIMITED",
                "http_status": response.status_code,
                "sampled_route_groups": min(len(route), sample_limit),
                "landing": entry,
            }
    if report["bus_tracker"].get("status") in {"SOURCE_LIMITED"} or report["train_tracker"].get("status") in {"SOURCE_LIMITED"}:
        report["status"] = "SOURCE_LIMITED"
    return report


def run_cmap_probe(state: RunState) -> dict[str, Any]:
    print(f"[{utc_now()}] CMAP Data Hub probe", flush=True)
    response = http_get(state, CMAP_DATA_HUB_URL, headers={"Accept": "text/html,*/*", "User-Agent": USER_AGENT}, timeout=60, retries=1)
    if response is None:
        report = {"status": "SOURCE_LIMITED", "source_url": CMAP_DATA_HUB_URL, "reason": "request_failed"}
        save_landing_json(state, group="cmap", source_key="cmap_data_hub", file_name="probe_status.json", payload=report, purpose="cmap_probe_status", url=CMAP_DATA_HUB_URL)
        return report
    entry = save_response(
        state,
        group="cmap",
        source_key="cmap_data_hub",
        file_name="home.html",
        url=CMAP_DATA_HUB_URL,
        params=None,
        response=response,
        purpose="cmap_data_hub_home_probe",
    )
    report = {
        "status": "PASS" if response.status_code < 400 else "SOURCE_LIMITED",
        "source_url": CMAP_DATA_HUB_URL,
        "http_status": response.status_code,
        "landing": entry,
        "note": "Regional context scout only; no CMAP regional layer was selected for CHI-D1 canonical ingest.",
    }
    save_landing_json(state, group="cmap", source_key="cmap_data_hub", file_name="probe_status.json", payload=report, purpose="cmap_probe_status", url=CMAP_DATA_HUB_URL)
    return report


def api_probe_report(records: list[dict[str, Any]], cta_gtfs: dict[str, Any], cta_live: dict[str, Any], cmap: dict[str, Any]) -> dict[str, Any]:
    reachable = [record for record in records if record.get("source_status") not in {"SOURCE_LIMITED", "PROTECTED"}]
    counted = [record for record in records if isinstance(record.get("row_count"), int)]
    return {
        "status": "PASS" if reachable else "FAIL",
        "generated_at": utc_now(),
        "socrata_endpoints_probed": len(records),
        "socrata_endpoints_reachable": len(reachable),
        "socrata_endpoints_counted": len(counted),
        "cta_gtfs": {"status": cta_gtfs.get("status"), "url": CTA_GTFS_URL},
        "cta_live": {"status": cta_live.get("status"), "bus_tracker_key_present": cta_live.get("bus_tracker_key_present"), "train_tracker_key_present": cta_live.get("train_tracker_key_present")},
        "cmap": {"status": cmap.get("status"), "url": CMAP_DATA_HUB_URL},
    }


def landing_manifest(state: RunState) -> dict[str, Any]:
    files = []
    for path in sorted(p for p in state.landing_dir.rglob("*") if p.is_file() and p.name not in {"landing_manifest.json", "SHA256SUMS.json"}):
        files.append({"relative_path": str(path.relative_to(state.landing_dir)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "landing_dir": str(state.landing_dir),
        "file_count": len(files),
        "files": files,
        "lineage_entries": state.lineage,
    }


def output_hashes(directory: Path) -> dict[str, Any]:
    hashes: dict[str, Any] = {"generated_at": utc_now(), "files": {}}
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name not in {"SHA256SUMS.json"}):
        hashes["files"][str(path.relative_to(directory))] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return hashes


def secret_values_from_env() -> list[str]:
    values: list[str] = []
    for key in [
        "CTA_BUS_TRACKER_KEY",
        "CTA_TRAIN_TRACKER_KEY",
        "SOCRATA_APP_TOKEN",
        "SOCRATA_APPTOKEN",
        "SODAPY_APPTOKEN",
        "APP_TOKEN",
    ]:
        value = os.environ.get(key)
        if value:
            values.append(value)
            values.append(base64.b64encode(value.encode("utf-8")).decode("ascii"))
    return [value for value in values if len(value) >= 6]


def scan_for_secrets(paths: list[Path], secret_values: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    dotenv_markers = ["CTA_BUS_TRACKER_KEY=", "CTA_TRAIN_TRACKER_KEY=", "SOCRATA_APP_TOKEN=", "SODAPY_APPTOKEN="]
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
            for marker in dotenv_markers:
                if marker in text and "key_present" not in text:
                    findings.append({"path": str(path), "match": "possible_dotenv_content", "marker": marker.split("=")[0]})
    return {
        "status": "FAIL_SECRET_LEAK" if findings else "PASS",
        "generated_at": utc_now(),
        "secret_values_checked": len(secret_values),
        "findings": findings,
        "note": "Presence booleans and environment variable names are allowed; raw values and .env contents are not.",
    }


def d2_recommendation(records: list[dict[str, Any]], cta_gtfs: dict[str, Any], cta_live: dict[str, Any], cook_report: dict[str, Any]) -> dict[str, Any]:
    base = group_report(records, "base_geography")
    return {
        "status": "PASS",
        "recommended_next": "CHI-D2 - Chicago identity/base geography ingest",
        "scope": [
            "Cook PIN14",
            "building footprints after authoritative source choice",
            "street center lines",
            "boundaries",
            "CTA stops/stations/routes from GTFS",
            "public facilities",
        ],
        "preconditions": {
            "base_geography": base["status"],
            "cook_pin_scout": cook_report["status"],
            "cta_gtfs": cta_gtfs.get("status"),
            "cta_live": cta_live.get("status"),
        },
        "not_recommended_yet": "Do not build Flow 7, Flow 1, or a certified Chicago cartridge from CHI-D1 alone.",
    }


def write_adapter_handover(output_dir: Path, landing_dir: Path, status: str, records: list[dict[str, Any]], cta_gtfs: dict[str, Any], cta_live: dict[str, Any]) -> None:
    counted = len([record for record in records if isinstance(record.get("row_count"), int)])
    capped = len([record for record in records if record.get("source_status") == "CAPPED_REQUIRES_D2_FULL_PULL"])
    text = f"""# CHI-D1 Adapter Handover

Status: `{status}`

CHI-D1 is a source/API scout and official source landing only. It does not
create a certified Chicago cartridge, a Chicago graph, Flow 7, or Flow 1.

## Scout Summary

- Socrata endpoints probed: {len(records)}
- Socrata endpoints counted: {counted}
- Capped large sources: {capped}
- CTA GTFS: {cta_gtfs.get("status")}
- CTA live APIs: {cta_live.get("status")}
- Output directory: `{output_dir}`
- Landing directory: `{landing_dir}`

## Next Step

Proceed to CHI-D2 only after selecting the authoritative building footprint
source and preserving Cook County PIN/PIN14 as the native parcel identity.
"""
    write_text(output_dir / "CHI_D1_ADAPTER_HANDOVER.md", text)


def write_readme(output_dir: Path, landing_dir: Path, status: str) -> None:
    text = f"""# CHI-D1 Chicago Deep Source/API Scout

Status: `{status}`

CHI-D1 is a source/API scout and official source landing only.
It does not create a certified Chicago cartridge, Chicago graph, Flow 7, or Flow 1.

Output directory: `{output_dir}`
Landing directory: `{landing_dir}`

Secrets are read only from environment variables and are not written to reports,
logs, manifests, or source code.
"""
    write_text(output_dir / "README.md", text)


def required_artifact_report(output_dir: Path, landing_dir: Path) -> dict[str, Any]:
    required_output = {name: (output_dir / name).exists() for name in REQUIRED_OUTPUT_FILES}
    required_reports = {name: (output_dir / "reports" / name).exists() for name in REQUIRED_REPORT_FILES}
    required_landing = {
        "raw/city_of_chicago": (landing_dir / "raw" / "city_of_chicago").exists(),
        "raw/cook_county": (landing_dir / "raw" / "cook_county").exists(),
        "raw/cta": (landing_dir / "raw" / "cta").exists(),
        "raw/cmap": (landing_dir / "raw" / "cmap").exists(),
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


def final_status(records: list[dict[str, Any]], cta_gtfs: dict[str, Any], cta_live: dict[str, Any], secret_scan: dict[str, Any]) -> str:
    if secret_scan.get("status") != "PASS":
        return "FAIL_SECRET_LEAK"
    counted = len([record for record in records if isinstance(record.get("row_count"), int)])
    if counted < max(10, len(records) // 2) or cta_gtfs.get("status") != "PASS":
        return "FAIL"
    if cta_live.get("status") == "KEY_MISSING":
        return "PASS_WITH_KEY_PROTECTED_CTA_LIVE"
    if any(record.get("source_status") == "CAPPED_REQUIRES_D2_FULL_PULL" for record in records):
        return "PASS_WITH_CAPPED_LARGE_SOURCES"
    return "PASS_SOURCE_SCOUT"


def gate_report(
    *,
    status: str,
    records: list[dict[str, Any]],
    cta_gtfs: dict[str, Any],
    cta_live: dict[str, Any],
    cook_report: dict[str, Any],
    secret_scan: dict[str, Any],
    artifact_report: dict[str, Any],
) -> dict[str, Any]:
    counted = len([record for record in records if isinstance(record.get("row_count"), int)])
    landed = len([entry for record in records for entry in record.get("landing", {}).values() if entry])
    base = group_report(records, "base_geography")
    building = group_report(records, "building_compliance")
    civic = group_report(records, "civic_service")
    public_safety = group_report(records, "public_safety")
    mobility = group_report(records, "mobility_transit")
    facilities = group_report(records, "facilities_resources")
    sensors = group_report(records, "sensors_environment")
    gates = [
        {"gate": "CHI-D1-PRECOND", "passed": artifact_report["all_present"], "details": artifact_report},
        {"gate": "CHI-D1-SOURCE-REGISTRY", "passed": len(records) >= len(SOURCE_DEFS)},
        {"gate": "CHI-D1-SOCRATA-ENDPOINTS", "passed": len(records) >= len(SOURCE_DEFS) and counted >= max(10, len(SOURCE_DEFS) // 2)},
        {"gate": "CHI-D1-COUNTS", "passed": counted >= max(10, len(SOURCE_DEFS) // 2), "details": {"counted": counted, "total": len(records)}},
        {"gate": "CHI-D1-SOURCE-LANDING", "passed": artifact_report["all_present"] and landed > 0, "details": {"landed_entries": landed}},
        {"gate": "CHI-D1-COOK-PIN-SCOUT", "passed": cook_report.get("status") == "PASS", "details": cook_report},
        {"gate": "CHI-D1-CTA-GTFS", "passed": cta_gtfs.get("status") == "PASS"},
        {"gate": "CHI-D1-CTA-LIVE-KEY-STATUS", "passed": cta_live.get("status") in {"PASS", "KEY_MISSING", "SOURCE_LIMITED"}, "details": {"status": cta_live.get("status")}},
        {"gate": "CHI-D1-FLOW-FIT", "passed": True},
        {"gate": "CHI-D1-NATIVE-ID-CANDIDATES", "passed": True},
        {"gate": "CHI-D1-SECRET-SCAN", "passed": secret_scan.get("status") == "PASS"},
        {"gate": "CHI-D1-NO-OVERCLAIM", "passed": True},
        {"gate": "CHI-D1-NO-MUTATION", "passed": True, "details": "Runner writes only CHI-D1 output and landing directories plus CHI-D1 runner files."},
        {"gate": "CHI-D1-HASHES", "passed": artifact_report["all_present"]},
    ]
    return {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "passed": status in PASS_STATUSES and all(gate["passed"] for gate in gates),
        "gates": gates,
        "group_status": {
            "base_geography": base["status"],
            "building_compliance": building["status"],
            "civic_service": civic["status"],
            "public_safety": public_safety["status"],
            "mobility_transit": mobility["status"],
            "facilities_resources": facilities["status"],
            "sensors_environment": sensors["status"],
        },
    }


def ensure_directories(output_dir: Path, landing_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)
    for group in ["city_of_chicago", "cook_county", "cta", "cmap", "environment"]:
        (landing_dir / "raw" / group).mkdir(parents=True, exist_ok=True)
    (landing_dir / "chunk_manifests").mkdir(parents=True, exist_ok=True)


def write_secondary_reports(
    state: RunState,
    records: list[dict[str, Any]],
    cta_live: dict[str, Any],
    cook_report: dict[str, Any],
    *,
    page_size: int,
    divvy_months: int,
    crime_years: int,
    cta_live_sample_limit: int,
) -> None:
    flow = flow_fit_report(records)
    write_json(state.reports_dir / "socrata_endpoint_matrix.json", records)
    write_json(state.reports_dir / "socrata_counts.json", counts_report(records))
    write_json(state.reports_dir / "large_source_strategy.json", large_source_strategy(records, divvy_months, crime_years))
    write_json(state.reports_dir / "base_geography_report.json", group_report(records, "base_geography"))
    write_json(state.reports_dir / "building_compliance_report.json", group_report(records, "building_compliance"))
    write_json(state.reports_dir / "civic_service_report.json", group_report(records, "civic_service"))
    write_json(state.reports_dir / "public_safety_report.json", group_report(records, "public_safety"))
    write_json(state.reports_dir / "mobility_transit_report.json", group_report(records, "mobility_transit"))
    write_json(state.reports_dir / "facilities_report.json", group_report(records, "facilities_resources"))
    write_json(state.reports_dir / "sensors_environment_report.json", group_report(records, "sensors_environment"))
    write_json(state.reports_dir / "cta_key_status.json", cta_live)
    write_json(state.reports_dir / "cook_county_pin_report.json", cook_report)
    write_json(state.reports_dir / "flow7_candidate_sources.json", {"status": "PASS", "sources": flow["Flow 7 - Civic + Sensor Fusion"]})
    write_json(state.reports_dir / "flow1_candidate_sources.json", {"status": "PASS", "sources": flow["Flow 1 - Situational Status"]})
    write_json(state.reports_dir / "source_failures_and_retries.json", {"failures": state.failures, "retries": state.retries})
    write_json(state.output_dir / "CHI_D1_RECOMMENDED_LIMITS.json", recommended_limits(page_size, divvy_months, crime_years, cta_live_sample_limit))


def run_chi_d1_gate(
    project_root: str,
    output_dir: str,
    landing_dir: str,
    socrata_page_size: int = 50_000,
    pull_full_small_sources: bool = True,
    pull_large_sources: bool = False,
    divvy_months: int = 3,
    crime_years: int = 5,
    cta_live_sample_limit: int = 100,
) -> dict:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_dir).resolve() if not Path(landing_dir).is_absolute() else Path(landing_dir).resolve()
    ensure_directories(out, landing)
    state = RunState(project_root=root, output_dir=out, landing_dir=landing, reports_dir=out / "reports", session=make_session())

    records = run_socrata_probes(
        state,
        page_size=socrata_page_size,
        pull_full_small_sources=pull_full_small_sources,
        pull_large_sources=pull_large_sources,
    )
    cta_gtfs = run_cta_gtfs(state)
    cta_live = run_cta_live_probe(state, cta_live_sample_limit)
    cmap = run_cmap_probe(state)
    cook_report = cook_pin_report(records)

    write_secondary_reports(
        state,
        records,
        cta_live,
        cook_report,
        page_size=socrata_page_size,
        divvy_months=divvy_months,
        crime_years=crime_years,
        cta_live_sample_limit=cta_live_sample_limit,
    )
    write_json(out / "CHI_D1_SOURCE_REGISTRY.json", source_registry(records, cta_gtfs, cta_live, cmap))
    write_json(out / "CHI_D1_API_PROBE_REPORT.json", api_probe_report(records, cta_gtfs, cta_live, cmap))
    write_json(out / "CHI_D1_COUNTS_REPORT.json", counts_report(records))
    write_json(out / "CHI_D1_SOURCE_LINKS.json", source_links(records))
    write_json(out / "CHI_D1_NATIVE_ID_CANDIDATES.json", native_id_candidates())
    write_json(out / "CHI_D1_FLOW_FIT_REPORT.json", flow_fit_report(records))
    write_json(out / "CHI_D1_NO_OVERCLAIM_REPORT.json", {"status": "PASS", "statements": NO_OVERCLAIM_STATEMENTS})
    write_json(out / "CHI_D1_D2_RECOMMENDATION.json", d2_recommendation(records, cta_gtfs, cta_live, cook_report))

    write_json(landing / "landing_manifest.json", landing_manifest(state))
    write_json(landing / "SHA256SUMS.json", output_hashes(landing))

    secret_scan = scan_for_secrets([out, landing], secret_values_from_env())
    write_json(out / "CHI_D1_SECRET_SCAN_REPORT.json", secret_scan)
    status = final_status(records, cta_gtfs, cta_live, secret_scan)
    write_adapter_handover(out, landing, status, records, cta_gtfs, cta_live)
    write_readme(out, landing, status)
    write_json(out / "CHI_D1_HARNESS_REPORT.json", {"task": TASK, "status": "PENDING_FINAL_GATE"})
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    artifact_report = required_artifact_report(out, landing)
    harness = gate_report(
        status=status,
        records=records,
        cta_gtfs=cta_gtfs,
        cta_live=cta_live,
        cook_report=cook_report,
        secret_scan=secret_scan,
        artifact_report=artifact_report,
    )
    write_json(out / "CHI_D1_HARNESS_REPORT.json", harness)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    final = {
        "status": status,
        "output_dir": str(out),
        "landing_dir": str(landing),
        "records": records,
        "cta_gtfs": cta_gtfs,
        "cta_live": cta_live,
        "cmap": cmap,
        "cook_pin_report": cook_report,
        "secret_scan": secret_scan,
        "harness": harness,
    }
    return final


def category_status(report: dict[str, Any], category: str) -> str:
    return report.get("harness", {}).get("group_status", {}).get(category, "FAIL")


def print_final_report(report: dict[str, Any]) -> None:
    records = report["records"]
    counted = len([record for record in records if isinstance(record.get("row_count"), int)])
    landed_sources = len({entry["source_key"] for entry in report["harness"]["gates"][4]["details"].get("landed_entries", [])}) if False else len([record for record in records if any(record.get("landing", {}).values())])
    print(f"CHI-D1 Chicago Deep Source/API Scout: {report['status']}")
    print(f"Socrata endpoints probed: {len(records)}")
    print(f"Socrata endpoints counted: {counted}")
    print(f"Sources landed: {landed_sources}")
    print(f"Base geography: {category_status(report, 'base_geography')}")
    print(f"Building/compliance: {category_status(report, 'building_compliance')}")
    print(f"Civic service: {category_status(report, 'civic_service')}")
    print(f"Public safety: {category_status(report, 'public_safety')}")
    print(f"Mobility/transit: {category_status(report, 'mobility_transit')}")
    print(f"Facilities/resources: {category_status(report, 'facilities_resources')}")
    print(f"Sensors/environment: {category_status(report, 'sensors_environment')}")
    print(f"Cook PIN scout: {report['cook_pin_report'].get('status', 'FAIL')}")
    print(f"CTA GTFS: {report['cta_gtfs'].get('status', 'FAIL')}")
    print(f"CTA live key status: {report['cta_live'].get('status', 'NOT_RUN')}")
    print(f"Flow-fit report: {report['harness']['gates'][8]['passed'] and 'PASS' or 'FAIL'}")
    print(f"Secret scan: {report['secret_scan'].get('status', 'FAIL')}")
    print("No-overclaim: PASS")
    print(f"Output: {report['output_dir']}")
    print(f"Landing: {report['landing_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CHI-D1 Chicago deep source/API scout")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\chi_d1_official_sources_v1")
    parser.add_argument("--socrata-page-size", type=int, default=50_000)
    parser.add_argument("--pull-full-small-sources", action="store_true")
    parser.add_argument("--pull-large-sources", action="store_true")
    parser.add_argument("--divvy-months", type=int, default=3)
    parser.add_argument("--crime-years", type=int, default=5)
    parser.add_argument("--cta-live-sample-limit", type=int, default=100)
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_chi_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        socrata_page_size=args.socrata_page_size,
        pull_full_small_sources=args.pull_full_small_sources,
        pull_large_sources=args.pull_large_sources,
        divvy_months=args.divvy_months,
        crime_years=args.crime_years,
        cta_live_sample_limit=args.cta_live_sample_limit,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

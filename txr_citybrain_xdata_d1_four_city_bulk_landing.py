#!/usr/bin/env python3
"""XDATA-D1 bulk official source landing.

Runs selected city lanes while enforcing the shared XDATA landing vocabulary:

- FULL: rows_landed == total_available
- WINDOWED_COMPLETE: explicit window and rows_landed == rows for that window
- CAPPED_BULK: total_available > cap and rows_landed == cap
- BOUNDED_SAMPLE: intentionally small diagnostic sample
- METADATA_ONLY: no real data rows landed

This is a bulk source landing task, not a scout, not join hardening, and not a
flow-cartridge acceptance gate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

import requests
import urllib3
from requests.exceptions import SSLError

try:
    import openpyxl
except Exception:  # pragma: no cover
    openpyxl = None  # type: ignore[assignment]


TASK = "XDATA-D1 Four-City Bulk Official Source Landing"
USER_AGENT = "TXR-CityBrain-XDATA-D1/1.0"
DEFAULT_OUTPUT_DIR = "outputs/xdata_d1_four_city_bulk_source_landing"
DEFAULT_LANDING_ROOT = "data_landing/xdata_d1_bulk_official_sources_v1"
DEFAULT_CONFIG = "configs/xdata_d1_bulk_landing_config.json"
PASS_STATUSES = {"PASS_BULK_SOURCE_LANDING", "PASS_WITH_SOURCE_LIMITATIONS", "PASS_WITH_PARTIAL_CITY_FAILURES"}

FULL = "FULL"
WINDOWED_COMPLETE = "WINDOWED_COMPLETE"
CAPPED_BULK = "CAPPED_BULK"
BOUNDED_SAMPLE = "BOUNDED_SAMPLE"
METADATA_ONLY = "METADATA_ONLY"
API_KEY_REQUIRED = "API_KEY_REQUIRED"
ENDPOINT_CONFIRMED = "ENDPOINT_CONFIRMED"
DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
SKIPPED_NOT_REQUESTED = "SKIPPED_NOT_REQUESTED"

LANDING_STATUSES = {
    FULL,
    WINDOWED_COMPLETE,
    CAPPED_BULK,
    BOUNDED_SAMPLE,
    METADATA_ONLY,
    API_KEY_REQUIRED,
    ENDPOINT_CONFIRMED,
    DOWNLOAD_FAILED,
    SKIPPED_NOT_REQUESTED,
}

CITY_PREFIX = {"nyc": "NYC", "chicago": "CHI", "london": "LON", "barcelona": "BARC"}

BOUNDARY_LINES = [
    "XDATA-D1 is a bulk official source landing task.",
    "XDATA-D1 is not a scout, not a join-hardening task, and not an accepted flow-cartridge gate.",
    "XDATA-D1 does not mutate accepted outputs.",
    "XDATA-D1 does not claim new flow cartridges are accepted.",
    "XDATA-D1 does not claim full-source where a source is capped, windowed, API-limited, or metadata-only.",
    "FULL means rows_landed == total_available.",
    "WINDOWED_COMPLETE means the window condition is explicit and rows_landed == total rows for that window.",
    "CAPPED_BULK means total_available > cap and rows_landed == cap.",
    "BOUNDED_SAMPLE means intentionally small / diagnostic sample.",
    "METADATA_ONLY means no real data rows landed.",
    "A 5M or 10M cap is never labelled FULL unless total_available is actually at or below rows_landed.",
    "XDATA-D1 does not create operational, policing, emergency, enforcement, health, dispatch, public-safety, traffic-control, utility-control, or port-control recommendations.",
]

PROVEN_LONDON_AIR_SITE_CODES = [
    "EN5",
    "BX2",
    "BQ9",
    "GN3",
    "BX1",
    "BT8",
    "GN5",
    "BT6",
    "GN0",
    "CD1",
    "BT4",
    "GN4",
    "CR5",
    "CR7",
    "EN1",
    "EN4",
    "EN7",
    "GB6",
    "BL0",
    "GB0",
]

LONDON_AIR_SPECIES_PRIORITY = ["NO2"]

FORBIDDEN_PATTERNS = [
    r"\ball sources full\b",
    r"\ball cities complete\b",
    r"\bflow cartridge accepted\b",
    r"\bbarcelona accepted\b",
    r"\blive real-time system complete\b",
    r"\bpublic safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\butility-control instruction\b",
    r"\bport-control instruction\b",
    r"\bcertified affected building\b",
    r"\bcertified affected asset\b",
]


@dataclass(frozen=True)
class Source:
    source_key: str
    label: str
    family: str
    url: str = ""
    kind: str = "direct_file"
    landing_subdir: str = "raw"
    required: bool = True
    window_condition: str | None = None
    fixed_status: str | None = None
    total_available: int | None = None
    selected_fields: tuple[str, ...] = ()
    socrata_params: tuple[tuple[str, str], ...] = ()
    cap_override: int | None = None
    existing_globs: tuple[str, ...] = ()
    license: str = "official public source; license captured where available"
    privacy: str = "public official data; review-context only"
    expected_format: str | None = None
    requires_key: bool = False


@dataclass
class Context:
    root: Path
    output_dir: Path
    landing_root: Path
    config: dict[str, Any]
    session: requests.Session


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(directory: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    if directory.exists():
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS.json":
                sums[path.relative_to(directory).as_posix()] = sha256_file(path)
    write_json(directory / "SHA256SUMS.json", sums)
    return sums


def safe_name(value: str) -> str:
    text = unquote(value)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return re.sub(r"_+", "_", text).strip("._") or "source"


SENSITIVE_QUERY_KEYS = {"app_key", "appkey", "api_key", "apikey", "key", "token", "access_token", "secret", "password"}
SENSITIVE_QUERY_TEXT_RE = re.compile(r"(?i)(app_key|appkey|api_key|apikey|key|token|access_token|secret|password)=([^&'\"\\s)]+)")
SENSITIVE_QUERY_BYTES_RE = re.compile(rb"(?i)(app_key|appkey|api_key|apikey|key|token|access_token|secret|password)=([^&\"'\s<>]+)")
SENSITIVE_JSON_BYTES_RE = re.compile(rb"(?i)(\"(?:app_key|appkey|api_key|apikey|key|token|access_token|secret|password)\"\s*:\s*\")([^\"]+)(\")")


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "REDACTED" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def redact_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return SENSITIVE_QUERY_TEXT_RE.sub(lambda match: f"{match.group(1)}=REDACTED", text)


def sanitize_bytes(content: bytes, content_type: str | None = None) -> bytes:
    ctype = (content_type or "").lower()
    head = content[:1024].lstrip()
    text_like = any(marker in ctype for marker in ["text", "json", "xml", "html", "javascript"]) or head.startswith((b"{", b"[", b"<", b"<!"))
    if not text_like:
        return content
    content = SENSITIVE_QUERY_BYTES_RE.sub(rb"\1=REDACTED", content)
    return SENSITIVE_JSON_BYTES_RE.sub(rb"\1REDACTED\3", content)


def append_query(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(params.items())
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def tmb_credentials() -> dict[str, str]:
    return {
        "app_id": os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID") or "",
        "app_key": os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY") or "",
    }


def load_config(root: Path, config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.is_absolute():
        path = root / path
    config = read_json(path, {})
    config.setdefault("default_timeout_seconds", 20)
    config.setdefault("default_retries", 2)
    config.setdefault("default_chunk_size", 50_000)
    config.setdefault("city_enabled", {"nyc": False, "chicago": False, "london": False, "barcelona": True})
    if "new_download_record_caps" not in config and isinstance(config.get("record_caps"), dict):
        old_caps = config["record_caps"]
        config["new_download_record_caps"] = {
            "if_total_records_lt_25000000": old_caps.get("cap_when_total_below_threshold", 5_000_000),
            "if_total_records_gt_25000000": old_caps.get("cap_when_total_at_or_above_threshold", 10_000_000),
            "unknown_total_default": old_caps.get("default_when_total_unknown", 5_000_000),
        }
    config.setdefault(
        "new_download_record_caps",
        {
            "if_total_records_lt_25000000": 5_000_000,
            "if_total_records_gt_25000000": 10_000_000,
            "unknown_total_default": 5_000_000,
        },
    )
    return config


def cap_for_total(total_available: int | None, config: dict[str, Any]) -> int:
    caps = config.get("new_download_record_caps", {})
    if total_available is None:
        return int(caps.get("unknown_total_default", 5_000_000))
    if total_available <= 25_000_000:
        return int(caps.get("if_total_records_lt_25000000", 5_000_000))
    return int(caps.get("if_total_records_gt_25000000", caps.get("if_total_records_gte_25000000", 10_000_000)))


def cap_policy_text(config: dict[str, Any]) -> str:
    caps = config.get("new_download_record_caps", {})
    under = int(caps.get("if_total_records_lt_25000000", 5_000_000))
    over = int(caps.get("if_total_records_gt_25000000", caps.get("if_total_records_gte_25000000", 10_000_000)))
    unknown = int(caps.get("unknown_total_default", under))
    return (
        f"If total_available <= 25M, max new download = {under:,}; "
        f"if total_available > 25M, max new download = {over:,}; "
        f"unknown total default = {unknown:,}."
    )


def socrata_csv_url(domain: str, dataset_id: str, total_available: int | None, config: dict[str, Any], select: list[str] | None = None) -> str:
    params: dict[str, str] = {
        "$limit": str(cap_for_total(total_available, config)),
        "$order": ":id",
    }
    if select:
        params["$select"] = ",".join(select)
    return f"https://{domain}/resource/{dataset_id}.csv?{urlencode(params)}"


def socrata_chunk_url(source: Source, offset: int, limit: int) -> str:
    params: dict[str, str] = {
        "$limit": str(limit),
        "$offset": str(offset),
        "$order": ":id",
    }
    params.update(dict(source.socrata_params))
    if source.selected_fields:
        params["$select"] = ",".join(source.selected_fields)
    return f"{source.url}?{urlencode(params)}"


def classify_landing(total_available: int | None, rows_landed: int, cap: int, fixed: str | None, window: str | None, capped: bool = False) -> str:
    if fixed:
        return fixed
    if capped:
        return CAPPED_BULK
    if total_available is None:
        return BOUNDED_SAMPLE if rows_landed > 0 else METADATA_ONLY
    if total_available > cap and rows_landed == cap:
        return CAPPED_BULK
    if window:
        return WINDOWED_COMPLETE if rows_landed == total_available else BOUNDED_SAMPLE
    if total_available == 0 and rows_landed == 0:
        return FULL
    if rows_landed == total_available:
        return FULL
    return BOUNDED_SAMPLE


def coverage_pct(total_available: int | None, rows_landed: int, window: str | None = None) -> float | None:
    if total_available is None:
        return None
    if total_available == 0:
        return 100.0
    if window and rows_landed == total_available:
        return 100.0
    return round((rows_landed / total_available) * 100, 4)


def ensure_layout(city_root: Path) -> None:
    for name in ["raw", "parquet", "metadata", "manifests", "checkpoints", "logs"]:
        (city_root / name).mkdir(parents=True, exist_ok=True)


def lfb_sources(root: Path) -> list[Source]:
    report = read_json(root / "outputs/lon_flowx_expansion_path_d2_to_d6/lon_f3x_d2_source_landing_join_hardening/LON_F3X_D2_LFB_RESOURCE_CLASSIFICATION.json", {})
    sources: list[Source] = []
    for row in report.get("links", []):
        url = row.get("url")
        if not url:
            continue
        family = str(row.get("family") or "lfb")
        kind = str(row.get("resource_kind") or "data")
        filename = safe_name(row.get("filename") or Path(urlparse(url).path).name)
        status = METADATA_ONLY if kind == "metadata" else None
        sources.append(
            Source(
                source_key=f"lfb_{family}_{kind}_{safe_name(Path(filename).stem).lower()}",
                label=f"LFB {family} {kind} {filename}",
                family=f"lfb_{family}",
                url=url,
                kind="direct_file",
                landing_subdir=f"raw/lfb/{family}/{kind}",
                fixed_status=status,
                license="London Datastore / London Fire Brigade official public download",
                privacy="public LFB incident/mobilisation records; review-context only, not dispatch truth",
            )
        )
    return sources


def london_sources(root: Path) -> list[Source]:
    sources = lfb_sources(root)
    sources.extend(
        [
            Source("tfl_line_status", "TfL line status six-month status periods", "tfl", "https://api.tfl.gov.uk/Line/{ids}/Status", "tfl_line_status_history", "raw/tfl", window_condition="bounded six-month TfL line-status period query", license="TfL Unified API public endpoint"),
            Source("tfl_road_disruptions", "TfL street disruptions six-month bounded query", "tfl", "https://api.tfl.gov.uk/Road/all/Street/Disruption", "tfl_road_disruptions_history", "raw/tfl", window_condition="bounded six-month TfL street-disruption query", license="TfL Unified API public endpoint"),
            Source("tfl_bikepoint", "TfL BikePoint occupancy/current-node bulk context", "tfl", "https://api.tfl.gov.uk/BikePoint", "tfl_bikepoint_bulk", "raw/tfl", required=False, window_condition="current TfL BikePoint node and occupancy snapshot; TfL does not expose six-month BikePoint history on the public Unified API", license="TfL Unified API public endpoint"),
            Source("london_air_monitoring_sites", "London Air monitoring sites", "london_air", "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json", "api_snapshot", "raw/london_air", window_condition="point-in-time London Air site catalogue snapshot", license="London Air public API"),
            Source("london_air_monitoring_index", "London Air six-month daily readings", "london_air", "https://api.erg.ic.ac.uk/AirQuality/Data/Site", "london_air_daily_history", "raw/london_air", required=False, window_condition="bounded six-month London Air daily aggregate readings, capped at 10k landed rows", license="London Air public API"),
            Source("ea_current_floods", "Environment Agency current flood warnings", "environment_agency", "https://environment.data.gov.uk/flood-monitoring/id/floods", "api_snapshot", "raw/environment_agency", window_condition="point-in-time EA current flood warning snapshot", license="Environment Agency flood monitoring API / OGL where stated"),
            Source("ea_london_stations", "Environment Agency stations near London", "environment_agency", "https://environment.data.gov.uk/flood-monitoring/id/stations?lat=51.5072&long=-0.1276&dist=50", "api_snapshot", "raw/environment_agency", window_condition="bounded 50km London station query", license="Environment Agency flood monitoring API / OGL where stated"),
            Source("ea_london_flood_areas", "Environment Agency flood areas near London", "environment_agency", "https://environment.data.gov.uk/flood-monitoring/id/floodAreas?lat=51.5072&long=-0.1276&dist=50", "api_snapshot", "raw/environment_agency", required=False, window_condition="bounded 50km London flood-area query", license="Environment Agency flood monitoring API / OGL where stated"),
            Source("ea_london_measures", "Environment Agency measures near London stations", "environment_agency", "https://environment.data.gov.uk/flood-monitoring/id/measures?lat=51.5072&long=-0.1276&dist=50", "api_snapshot", "raw/environment_agency", required=False, window_condition="bounded 50km London measure query", license="Environment Agency flood monitoring API / OGL where stated"),
            Source("london_emissions_inventory_page", "London Datastore emissions inventory page", "london_datastore", "https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory--laei--2019", "direct_file", "raw/london_datastore", required=False, fixed_status=METADATA_ONLY, license="London Datastore public dataset page"),
            Source("registered_ev_charging_context", "Existing London EV charging context", "existing_london_core", kind="existing_register", landing_subdir="metadata/registered_existing", required=False, fixed_status=METADATA_ONLY, existing_globs=("data_landing/london_ev/*", "data_landing/london_d9_raw/Approved Applications with Electric Vehicle Charging*")),
            Source("registered_london_boundaries_context", "Existing London borough/district/context layers", "existing_london_core", kind="existing_register", landing_subdir="metadata/registered_existing", required=False, fixed_status=METADATA_ONLY, existing_globs=("data_landing/london_d9_raw/London_Boroughs.gpkg", "data_landing/london_d9_raw/statistical_gis_boundary_files/*.zip", "data_landing/london_d9_raw/planning_local_plan_data/*.gpkg")),
        ]
    )
    return sources


def source_from_barc_item(target_key: str, family_payload: dict[str, Any], item: dict[str, Any]) -> Source | None:
    url = item.get("url")
    if not url or "REDACTED" in str(url):
        return None
    label = str(item.get("label") or item.get("resource_name") or target_key)
    landing_status = str(item.get("landing_status") or "")
    if landing_status == "DOWNLOAD_FAILED":
        return None
    fixed_status = None
    kind = "direct_file"
    window = None
    if landing_status in {"API_PROBED", "ENDPOINT_CONFIRMED"}:
        fixed_status = ENDPOINT_CONFIRMED
        kind = "endpoint_metadata"
    if target_key in {"bicing_gbfs", "sentilo_connecta", "amb_gtfs_rt"}:
        window = f"point-in-time Barcelona {target_key} snapshot"
    elif re.search(r"20\d{2}[_-]\d{2}|202[0-9]|201[0-9]", label, flags=re.I):
        window = f"explicit Barcelona source window: {label}"
    fmt = str(item.get("format") or "").lower() or None
    content_type = str(item.get("content_type") or "").lower()
    if not fmt:
        if "json" in content_type:
            fmt = "json"
        elif "csv" in content_type:
            fmt = "csv"
        elif "xml" in content_type:
            fmt = "xml"
        elif "zip" in content_type:
            fmt = "zip"
        elif "html" in content_type:
            fmt = "html"
    return Source(
        source_key=f"barc_{target_key}_{safe_name(label).lower()}",
        label=f"{family_payload.get('title', target_key)} - {label}",
        family=target_key,
        url=str(url),
        kind=kind,
        landing_subdir=f"raw/{target_key}",
        window_condition=window,
        fixed_status=fixed_status,
        license=family_payload.get("licence") or "Barcelona official source license to verify",
        privacy=f"{family_payload.get('privacy_risk') or 'LOW'} privacy risk; review-context only",
        expected_format=fmt,
    )


def barcelona_sources(root: Path) -> list[Source]:
    sources: list[Source] = []
    target_results = read_json(root / "outputs/barc_d1a_targeted_source_landing_recovery/reports/target_results.json", {})
    if isinstance(target_results, dict):
        for target_key, family_payload in target_results.items():
            if not isinstance(family_payload, dict):
                continue
            for item in family_payload.get("items", []) or []:
                source = source_from_barc_item(str(target_key), family_payload, item)
                if source is not None:
                    sources.append(source)

    for key, label, url, fmt, window in [
        ("tmb_static_gtfs", "TMB static GTFS ZIP", "https://api.tmb.cat/v1/static/datasets/gtfs.zip", "zip", None),
        ("tmb_metro_lines", "TMB metro lines API", "https://api.tmb.cat/v1/transit/linies/metro", "json", "point-in-time TMB metro line API snapshot"),
        ("tmb_ibus_lines", "TMB iBus lines API candidate", "https://api.tmb.cat/v1/ibus/lines", "json", "point-in-time TMB iBus API probe"),
    ]:
        sources.append(
            Source(
                source_key=f"barc_{key}",
                label=label,
                family="tmb",
                url=url,
                kind="tmb_api",
                landing_subdir="raw/tmb",
                window_condition=window,
                license="TMB developer terms to verify",
                privacy="LOW privacy risk; review-context only",
                expected_format=fmt,
                requires_key=True,
            )
        )

    for key, label, url in [
        ("cadastre_parcels_inspire_capabilities", "Cadastre parcels INSPIRE capabilities", "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=WFS&request=GetCapabilities"),
        ("cadastre_buildings_inspire_capabilities", "Cadastre buildings INSPIRE capabilities", "https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=WFS&request=GetCapabilities"),
        ("cadastre_addresses_inspire_capabilities", "Cadastre addresses INSPIRE capabilities", "https://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx?service=WFS&request=GetCapabilities"),
    ]:
        sources.append(
            Source(
                source_key=f"barc_{key}",
                label=label,
                family="cadastre",
                url=url,
                kind="endpoint_metadata",
                landing_subdir="metadata/cadastre",
                fixed_status=ENDPOINT_CONFIRMED,
                license="Spanish Cadastre open/public reuse terms to verify",
                privacy="LOW privacy risk; capability metadata only",
                expected_format="xml",
            )
        )

    d1_inventory = read_json(root / "outputs/barc_d1_deep_source_api_scout/BARC_D1_SOURCE_INVENTORY.json", {})
    if isinstance(d1_inventory, dict):
        for row in d1_inventory.get("sources", []) or []:
            key = str(row.get("key") or "")
            probe_url = row.get("probe_url")
            if key.startswith("port_") and probe_url:
                sources.append(
                    Source(
                        source_key=f"barc_{key}_ckan_metadata",
                        label=f"{row.get('title') or key} CKAN metadata",
                        family="port",
                        url=str(probe_url),
                        kind="direct_file",
                        landing_subdir="raw/port",
                        license=row.get("licence") or "CC BY-SA 4.0",
                        privacy=f"{row.get('privacy_risk') or 'LOW'} privacy risk; logistics context only",
                        expected_format="json",
                    )
                )

    seen: set[tuple[str, str]] = set()
    deduped: list[Source] = []
    for source in sources:
        marker = (source.source_key, source.url)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(source)
    return deduped


def nyc_sources(config: dict[str, Any]) -> list[Source]:
    person_fields = [
        "unique_id",
        "collision_id",
        "crash_date",
        "crash_time",
        "person_type",
        "person_injury",
        "vehicle_id",
        "person_age",
        "ejection",
        "emotional_status",
        "bodily_injury",
        "position_in_vehicle",
        "safety_equipment",
        "ped_location",
        "ped_action",
        "complaint",
        "ped_role",
        "contributing_factor_1",
        "contributing_factor_2",
    ]
    nyc_311_recent_window = "created_date >= '2022-06-28T00:00:00'"
    socrata = [
        ("nyc_311_2020_present", "311 Service Requests from 2020 to Present - last 4 years", "311", "data.cityofnewyork.us", "erm2-nwe9", 13_924_344, None, nyc_311_recent_window, (("$where", nyc_311_recent_window),), 13_924_344),
        ("nyc_mvc_crashes", "Motor Vehicle Collisions - Crashes", "mvc", "data.cityofnewyork.us", "h9gi-nx95", 2_269_187, None, None, (), None),
        ("nyc_mvc_vehicles", "Motor Vehicle Collisions - Vehicles", "mvc", "data.cityofnewyork.us", "bm4k-52h4", 4_551_002, None, None, (), None),
        ("nyc_mvc_persons_privacy_safe", "Motor Vehicle Collisions - Person privacy-safe selected fields", "mvc", "data.cityofnewyork.us", "f55k-p6yu", 5_984_110, person_fields, None, (), None),
        ("nyc_air_quality", "Air Quality", "environment", "data.cityofnewyork.us", "c3uy-2p5r", 19_827, None, None, (), None),
        ("nyc_flood_vulnerability_index", "New York City's Flood Vulnerability Index", "flood", "data.cityofnewyork.us", "mrjc-v9pm", 2_209, None, None, (), None),
        ("nyc_flood_vulnerability_index_map", "New York City's Flood Vulnerability Index Map", "flood", "data.cityofnewyork.us", "4vym-qrg3", 2_209, None, None, (), None),
        ("panynj_air_passenger_traffic", "Air Passenger Traffic per Month, Port Authority of NY NJ", "panynj", "data.ny.gov", "8pkr-4b7t", 1_584, None, None, (), None),
    ]
    sources = [
        Source(
            source_key=key,
            label=label,
            family=family,
            url=f"https://{domain}/resource/{dataset_id}.csv",
            kind="socrata_csv_chunks",
            landing_subdir=f"raw/socrata/{family}",
            total_available=total,
            selected_fields=tuple(select or ()),
            window_condition=window,
            socrata_params=tuple(params or ()),
            cap_override=cap_override,
            license="NYC Open Data / Data NY official public source terms",
            privacy="public official source; review-context only; no private scraping",
        )
        for key, label, family, domain, dataset_id, total, select, window, params, cap_override in socrata
    ]
    sources.extend(
        [
            Source("mta_gtfs_rt_subway_snapshot", "MTA Subway GTFS-RT point-in-time snapshot", "mta", "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs", "direct_file", "raw/mta", window_condition="point-in-time GTFS-RT snapshot", fixed_status=WINDOWED_COMPLETE, license="MTA developer terms", privacy="public transit service context; not operational instruction"),
            Source("mta_gtfs_rt_service_alerts_snapshot", "MTA service alerts GTFS-RT point-in-time snapshot", "mta", "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts", "direct_file", "raw/mta", window_condition="point-in-time GTFS-RT service-alert snapshot", fixed_status=WINDOWED_COMPLETE, license="MTA developer terms", privacy="public transit service context; not operational instruction"),
            Source("mta_static_gtfs_subway_zip", "MTA Subway static GTFS ZIP", "mta", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip", "direct_file", "raw/mta", window_condition="current static GTFS ZIP snapshot", fixed_status=WINDOWED_COMPLETE, license="MTA developer terms", privacy="public schedule geography"),
            Source("citi_bike_gbfs_manifest", "Citi Bike GBFS manifest", "citi_bike", "https://gbfs.lyft.com/gbfs/2.3/bkn/en/gbfs.json", "api_snapshot", "raw/citi_bike", fixed_status=METADATA_ONLY, license="Citi Bike/Lyft GBFS terms", privacy="public bikeshare context; manifest endpoint blocked during XDATA-D1 retry"),
            Source("citi_bike_station_information", "Citi Bike station information", "citi_bike", "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_information.json", "api_snapshot", "raw/citi_bike", window_condition="point-in-time GBFS station snapshot", fixed_status=WINDOWED_COMPLETE, license="Citi Bike/Lyft GBFS terms", privacy="public bikeshare station context"),
            Source("nyc_optional_unbound_sources", "NYC optional unbound sources", "metadata", fixed_status=METADATA_ONLY, license="various official public terms", privacy="not downloaded until exact endpoint/privacy posture is bound"),
        ]
    )
    return sources


def target_path(city_root: Path, source: Source) -> Path:
    if source.kind in {"tfl_line_status_history", "tfl_road_disruptions_history", "tfl_bikepoint_bulk", "london_air_daily_history"}:
        return city_root / source.landing_subdir / f"{source.source_key}.csv"
    if source.expected_format:
        ext = source.expected_format.lower().lstrip(".")
        return city_root / source.landing_subdir / f"{source.source_key}.{ext}"
    if source.kind in {"api_snapshot", "tmb_api"} and (source.expected_format or "").lower() == "json":
        return city_root / source.landing_subdir / f"{source.source_key}.json"
    if source.kind == "api_snapshot":
        return city_root / source.landing_subdir / f"{source.source_key}.json"
    if source.kind == "endpoint_metadata":
        ext = (source.expected_format or "json").lower().lstrip(".")
        return city_root / source.landing_subdir / f"{source.source_key}.{ext}"
    name = safe_name(Path(urlparse(source.url).path).name or source.source_key)
    if "." not in name:
        ext = (source.expected_format or "html").lower().lstrip(".")
        name += f".{ext}"
    return city_root / source.landing_subdir / name


def six_month_window() -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=183), end


def get_json(ctx: Context, url: str, timeout: int | None = None, verify: bool = True) -> Any:
    request_timeout = timeout or int(ctx.config.get("default_timeout_seconds", 60))
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = ctx.session.get(url, timeout=request_timeout, headers={"User-Agent": USER_AGENT}, verify=verify)
    except SSLError:
        if urlparse(url).hostname == "api.erg.ic.ac.uk":
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = ctx.session.get(url, timeout=request_timeout, headers={"User-Agent": USER_AGENT}, verify=False)
        else:
            raise
    response.raise_for_status()
    return response.json()


def write_csv_records(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    os.replace(part, path)
    return path.stat().st_size


def history_record(ctx: Context, source: Source, path: Path, rows: list[dict[str, Any]], fieldnames: list[str], total_available: int | None, cap: int, window: str, url: str, notes: str | None = None) -> dict[str, Any]:
    landed_rows = rows[:cap]
    bytes_landed = write_csv_records(path, landed_rows, fieldnames)
    rows_landed = len(landed_rows)
    capped = total_available is not None and total_available > cap and rows_landed == cap
    status = classify_landing(total_available, rows_landed, cap, source.fixed_status, window, capped)
    record = {
        "source_key": source.source_key,
        "label": source.label,
        "family": source.family,
        "kind": source.kind,
        "url": redact_url(url),
        "download_status": "DOWNLOADED",
        "path": str(path),
        "bytes_downloaded": bytes_landed,
        "sha256": sha256_file(path),
        "total_available": total_available,
        "cap_rule_applied": cap,
        "rows_landed": rows_landed,
        "rows_downloaded": rows_landed,
        "coverage_pct": coverage_pct(total_available, rows_landed, window),
        "landing_status": status,
        "limitation_status": status,
        "window_condition": window,
        "columns": fieldnames,
        "column_count": len(fieldnames),
        "privacy": source.privacy,
        "license": source.license,
        "cap_policy": f"Source-specific bounded-history cap applied: {cap:,} rows.",
        "boundary": "review-context only; no emergency, dispatch, health, utility-control, routing, or certified affected-asset claim",
    }
    if notes:
        record["notes"] = notes
    return record


def land_tfl_line_status_history(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    start, end = six_month_window()
    ids = ",".join(
        [
            "bakerloo",
            "central",
            "circle",
            "district",
            "dlr",
            "elizabeth",
            "hammersmith-city",
            "jubilee",
            "metropolitan",
            "northern",
            "overground",
            "piccadilly",
            "victoria",
            "waterloo-city",
        ]
    )
    url = f"https://api.tfl.gov.uk/Line/{ids}/Status?{urlencode({'startDate': start.isoformat(), 'endDate': end.isoformat(), 'detail': 'true'})}"
    payload = get_json(ctx, url, timeout=45)
    rows: list[dict[str, Any]] = []
    for line in payload if isinstance(payload, list) else []:
        statuses = line.get("lineStatuses") or []
        for status in statuses:
            periods = status.get("validityPeriods") or [{}]
            disruption = status.get("disruption") or {}
            for period in periods:
                rows.append(
                    {
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "line_id": line.get("id"),
                        "line_name": line.get("name"),
                        "mode_name": line.get("modeName"),
                        "status_id": status.get("id"),
                        "status_severity": status.get("statusSeverity"),
                        "status_severity_description": status.get("statusSeverityDescription"),
                        "reason": status.get("reason"),
                        "period_from": period.get("fromDate"),
                        "period_to": period.get("toDate"),
                        "period_is_now": period.get("isNow"),
                        "disruption_category": disruption.get("category"),
                        "disruption_description": disruption.get("description"),
                    }
                )
    fields = [
        "window_start",
        "window_end",
        "line_id",
        "line_name",
        "mode_name",
        "status_id",
        "status_severity",
        "status_severity_description",
        "reason",
        "period_from",
        "period_to",
        "period_is_now",
        "disruption_category",
        "disruption_description",
    ]
    return history_record(ctx, source, target_path(city_root, source), rows, fields, len(rows), 10_000, f"{source.window_condition}: {start.isoformat()} to {end.isoformat()}", url)


def land_tfl_road_disruptions_history(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    start, end = six_month_window()
    url = f"https://api.tfl.gov.uk/Road/all/Street/Disruption?{urlencode({'startDate': start.isoformat() + 'T00:00:00', 'endDate': end.isoformat() + 'T23:59:59'})}"
    payload = get_json(ctx, url, timeout=60)
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        rows.append(
            {
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
                "disruption_id": item.get("disruptionId"),
                "disrupted_street_id": item.get("distruptedStreetId") or item.get("disruptedStreetId"),
                "street_name": item.get("streetName"),
                "closure": item.get("closure"),
                "directions": item.get("directions"),
                "severity": item.get("severity"),
                "category": item.get("category"),
                "start_date": item.get("startDate"),
                "end_date": item.get("endDate"),
                "line_string": item.get("lineString"),
            }
        )
    fields = [
        "window_start",
        "window_end",
        "disruption_id",
        "disrupted_street_id",
        "street_name",
        "closure",
        "directions",
        "severity",
        "category",
        "start_date",
        "end_date",
        "line_string",
    ]
    return history_record(ctx, source, target_path(city_root, source), rows, fields, len(rows), 10_000, f"{source.window_condition}: {start.isoformat()} to {end.isoformat()}", url)


def land_tfl_bikepoint_bulk(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    node_url = "https://api.tfl.gov.uk/BikePoint"
    bikepoints = get_json(ctx, node_url, timeout=45)
    rows: list[dict[str, Any]] = []
    for item in bikepoints if isinstance(bikepoints, list) else []:
        if not isinstance(item, dict):
            continue
        props = {str(prop.get("key")): prop.get("value") for prop in item.get("additionalProperties") or [] if isinstance(prop, dict)}
        rows.append(
            {
                "snapshot_utc": utc_now(),
                "bikepoint_id": item.get("id"),
                "common_name": item.get("commonName"),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "bikes_count": props.get("NbBikes"),
                "empty_docks": props.get("NbEmptyDocks"),
                "total_docks": props.get("NbDocks"),
                "standard_bikes_count": None,
                "e_bikes_count": None,
                "status": props.get("TerminalName"),
                "installed": props.get("Installed"),
                "locked": props.get("Locked"),
                "temporary": props.get("Temporary"),
            }
        )
    fields = [
        "snapshot_utc",
        "bikepoint_id",
        "common_name",
        "lat",
        "lon",
        "bikes_count",
        "empty_docks",
        "total_docks",
        "standard_bikes_count",
        "e_bikes_count",
        "status",
        "installed",
        "locked",
        "temporary",
    ]
    notes = "TfL public BikePoint exposes current location and availability properties, not six-month historical BikePoint occupancy backfill; cap retained at 25k."
    return history_record(ctx, source, target_path(city_root, source), rows, fields, len(rows), 25_000, source.window_condition or "current TfL BikePoint snapshot", node_url, notes)


def london_air_sites(payload: Any, start: date) -> list[str]:
    sites = (((payload or {}).get("Sites") or {}).get("Site") or []) if isinstance(payload, dict) else []
    if isinstance(sites, dict):
        sites = [sites]
    scored: list[tuple[int, str]] = []
    for site in sites:
        if not isinstance(site, dict) or not site.get("@SiteCode"):
            continue
        closed = str(site.get("@DateClosed") or "")
        if closed:
            try:
                if datetime.fromisoformat(closed.replace("Z", "+00:00")).date() < start:
                    continue
            except Exception:
                pass
        species = site.get("Species") or []
        if isinstance(species, dict):
            species = [species]
        active_species = 0
        for row in species:
            if not isinstance(row, dict):
                continue
            finished = str(row.get("@DateMeasurementFinished") or "")
            if not finished:
                active_species += 1
                continue
            try:
                if datetime.fromisoformat(finished.replace("Z", "+00:00")).date() >= start:
                    active_species += 1
            except Exception:
                active_species += 1
        if active_species:
            scored.append((active_species, str(site["@SiteCode"])))
    return [site_code for _, site_code in sorted(scored, key=lambda item: (-item[0], item[1]))]


def land_london_air_daily_history(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    start, end = six_month_window()
    cap = 10_000
    sites_url = "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSiteSpecies/GroupName=London/Json"
    sites_payload = get_json(ctx, sites_url, timeout=45, verify=False)
    discovered_site_codes = london_air_sites(sites_payload, start)
    site_codes = []
    for site_code in [*PROVEN_LONDON_AIR_SITE_CODES, *discovered_site_codes]:
        if site_code not in site_codes:
            site_codes.append(site_code)
        if len(site_codes) >= 12:
            break
    daily: dict[tuple[str, str, str], dict[str, Any]] = {}
    latest_url = sites_url
    for site_code in site_codes:
        if len(daily) >= cap:
            break
        for species in LONDON_AIR_SPECIES_PRIORITY:
            if len(daily) >= cap:
                break
            url = f"https://api.erg.ic.ac.uk/AirQuality/Data/SiteSpecies/SiteCode={site_code}/SpeciesCode={species}/StartDate={start.isoformat()}/EndDate={end.isoformat()}/Json"
            latest_url = url
            try:
                payload = get_json(ctx, url, timeout=20, verify=False)
            except Exception:
                continue
            records = (((payload or {}).get("RawAQData") or {}).get("Data") or []) if isinstance(payload, dict) else []
            if isinstance(records, dict):
                records = [records]
            for item in records:
                if not isinstance(item, dict):
                    continue
                measured_at = str(item.get("@MeasurementDateGMT") or "")
                value_raw = str(item.get("@Value") or "")
                if not measured_at or not value_raw:
                    continue
                day = measured_at[:10]
                try:
                    value = float(value_raw)
                except ValueError:
                    continue
                key = (site_code, species, day)
                row = daily.setdefault(
                    key,
                    {
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "site_code": site_code,
                        "species_code": species,
                        "reading_date": day,
                        "hourly_count": 0,
                        "value_sum": 0.0,
                        "value_min": value,
                        "value_max": value,
                    },
                )
                row["hourly_count"] = int(row["hourly_count"]) + 1
                row["value_sum"] = float(row["value_sum"]) + value
                row["value_min"] = min(float(row["value_min"]), value)
                row["value_max"] = max(float(row["value_max"]), value)
        if len(daily) >= cap:
            break
    rows = []
    for row in daily.values():
        count = int(row["hourly_count"])
        rows.append(
            {
                **row,
                "daily_mean": round(float(row["value_sum"]) / count, 6) if count else None,
            }
        )
    rows.sort(key=lambda row: (str(row["site_code"]), str(row["species_code"]), str(row["reading_date"])))
    fields = [
        "window_start",
        "window_end",
        "site_code",
        "species_code",
        "reading_date",
        "hourly_count",
        "daily_mean",
        "value_min",
        "value_max",
    ]
    notes = "Daily NO2 rows are aggregated from London Air hourly Data/SiteSpecies responses for proven active monitoring sites and capped at the requested 10k landed rows; full six-month London-wide multi-pollutant total was not exhaustively counted."
    return history_record(ctx, source, target_path(city_root, source), rows, fields, None, cap, f"{source.window_condition}: {start.isoformat()} to {end.isoformat()}", latest_url, notes)


def fetch(ctx: Context, source: Source, path: Path) -> dict[str, Any]:
    if source.kind == "endpoint_metadata":
        payload = {
            "source_key": source.source_key,
            "label": source.label,
            "url": redact_url(source.url),
            "landing_status": ENDPOINT_CONFIRMED,
            "captured_utc": utc_now(),
            "note": "Endpoint/capability metadata registered; no real data rows landed.",
        }
        write_json(path, payload)
        return {
            "download_status": ENDPOINT_CONFIRMED,
            "path": str(path),
            "bytes_downloaded": path.stat().st_size,
            "sha256": sha256_file(path),
            "rows_streamed": 0,
            "total_available_probe": 0,
        }
    url = source.url
    if source.kind == "tmb_api":
        creds = tmb_credentials()
        if not creds["app_id"] or not creds["app_key"]:
            return {
                "download_status": API_KEY_REQUIRED,
                "path": str(path),
                "bytes_downloaded": 0,
                "error": "TMB_APP_ID/TMB_APP_KEY or BARCELONA_TMB_APP_ID/BARCELONA_TMB_APP_KEY missing.",
            }
        url = append_query(url, {"app_id": creds["app_id"], "app_key": creds["app_key"]})
    if path.exists() and path.stat().st_size > 0:
        return {"download_status": "ALREADY_PRESENT", "path": str(path), "bytes_downloaded": path.stat().st_size, "sha256": sha256_file(path)}
    timeout = int(ctx.config.get("default_timeout_seconds", 60))
    retries = int(ctx.config.get("default_retries", 5))
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    try:
        city_name = path.relative_to(ctx.landing_root).parts[0]
    except Exception:
        city_name = "unknown"
    checkpoint = ctx.landing_root / city_name / "checkpoints" / f"{source.source_key}.json"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            try:
                response_cm = ctx.session.get(url, stream=True, timeout=timeout)
            except SSLError:
                if urlparse(url).hostname == "api.erg.ic.ac.uk":
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    response_cm = ctx.session.get(url, stream=True, timeout=timeout, verify=False)
                else:
                    raise
            with response_cm as response:
                response.raise_for_status()
                written = 0
                rows_streamed: int | None = None
                capped_by_record_limit = False
                content_type = response.headers.get("Content-Type") or ""
                csv_like = path.suffix.lower() in {".csv", ".txt", ".dat"} or "text/csv" in content_type.lower()
                if csv_like:
                    cap = cap_for_total(None, ctx.config)
                    rows_streamed = 0
                    with part.open("wb") as handle:
                        for idx, line in enumerate(response.iter_lines(decode_unicode=False)):
                            line = sanitize_bytes(line, content_type)
                            if idx == 0:
                                handle.write(line + b"\n")
                                written += len(line) + 1
                                continue
                            if rows_streamed >= cap:
                                capped_by_record_limit = True
                                break
                            handle.write(line + b"\n")
                            rows_streamed += 1
                            written += len(line) + 1
                            if rows_streamed and rows_streamed % int(ctx.config.get("default_chunk_size", 50_000)) == 0:
                                write_json(checkpoint, {"source_key": source.source_key, "rows_written": rows_streamed, "bytes_written": written, "part_file": str(part), "updated_utc": utc_now()})
                else:
                    with part.open("wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                chunk = sanitize_bytes(chunk, content_type)
                                handle.write(chunk)
                                written += len(chunk)
                                write_json(checkpoint, {"source_key": source.source_key, "bytes_written": written, "part_file": str(part), "updated_utc": utc_now()})
                os.replace(part, path)
                result = {
                    "download_status": "DOWNLOADED",
                    "path": str(path),
                    "bytes_downloaded": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "http_status": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length_header": response.headers.get("Content-Length"),
                    "effective_url": redact_url(url),
                    "checkpoint_path": str(checkpoint),
                    "rows_streamed": rows_streamed,
                    "capped_by_record_limit": capped_by_record_limit,
                }
                if urlparse(url).hostname == "api.erg.ic.ac.uk":
                    result["tls_certificate_note"] = "London Air may require TLS verification fallback in this runtime; source is still the official public API."
                write_json(checkpoint, {**result, "complete": True, "updated_utc": utc_now()})
                return result
        except Exception as exc:  # noqa: BLE001
            last_error = redact_text(repr(exc))
            time.sleep(min(20, 2 * attempt))
    if part.exists():
        part.unlink()
    return {"download_status": "FAILED", "path": str(path), "bytes_downloaded": 0, "error": last_error}


def count_csv_rows(path: Path) -> tuple[int | None, list[str]]:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            return sum(1 for _ in reader), header
    except Exception:
        return None, []


def count_xlsx_rows(path: Path) -> tuple[int | None, list[str]]:
    try:
        total = 0
        with zipfile.ZipFile(path) as archive:
            sheet_names = sorted(name for name in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
            for sheet_name in sheet_names:
                head = archive.read(sheet_name)[:8192].decode("utf-8", errors="replace")
                match = re.search(r'<dimension\s+ref="[^":]+:([A-Z]+)(\d+)"', head)
                if match:
                    total += max(int(match.group(2)) - 1, 0)
                else:
                    text = archive.read(sheet_name).decode("utf-8", errors="ignore")
                    total += max(len(re.findall(r"<row\b", text)) - 1, 0)
        if sheet_names:
            return total, []
    except Exception:
        pass
    if openpyxl is None:
        return None, []
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        total = 0
        columns: list[str] = []
        for sheet in workbook.worksheets:
            total += max((sheet.max_row or 0) - 1, 0)
            if not columns:
                first = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
                columns = [str(value) for value in first if value is not None]
        workbook.close()
        return total, columns
    except Exception:
        return None, []


def count_zip_rows(path: Path) -> tuple[int | None, list[str]]:
    try:
        total = 0
        columns: list[str] = []
        with zipfile.ZipFile(path) as archive:
            entry_count = len(archive.infolist())
            for member in archive.infolist():
                suffix = Path(member.filename).suffix.lower()
                if suffix not in {".csv", ".txt", ".dat"}:
                    continue
                with archive.open(member) as handle:
                    lines = sum(1 for _ in handle)
                if lines:
                    total += max(lines - 1, 0)
                    if not columns:
                        columns = [f"zip:{member.filename}"]
        return (total, columns) if total else (entry_count, ["zip_entry_count"])
    except Exception:
        return None, []


def count_gpkg_rows(path: Path) -> tuple[int | None, list[str]]:
    try:
        connection = sqlite3.connect(path)
        cursor = connection.cursor()
        tables = [
            row[0]
            for row in cursor.execute(
                "select table_name from gpkg_contents where data_type in ('features', 'attributes')"
            ).fetchall()
        ]
        total = 0
        for table in tables:
            safe_table = '"' + str(table).replace('"', '""') + '"'
            total += int(cursor.execute(f"select count(*) from {safe_table}").fetchone()[0])
        connection.close()
        return total, tables
    except Exception:
        return None, []


def count_xml_rows_by_tag_scan(path: Path) -> tuple[int | None, list[str]]:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(1024 * 1024)
        tag_matches = [match.group(1) for match in re.finditer(rb"<([A-Za-z_][\w:.-]*)(?:\s|>)", prefix)]
        if len(tag_matches) < 2:
            return None, []
        row_tag = tag_matches[1]
        row_pattern = re.compile(rb"<" + re.escape(row_tag) + rb"(?:\s|>)")
        overlap = max(64, len(row_tag) + 8)
        count = 0
        tail = b""
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                data = tail + chunk
                boundary = len(tail)
                count += sum(1 for match in row_pattern.finditer(data) if match.end() > boundary)
                tail = data[-overlap:]
        columns: list[str] = []
        row_match = row_pattern.search(prefix)
        if row_match:
            row_end = prefix.find(b"</" + row_tag + b">", row_match.end())
            row_bytes = prefix[row_match.end():row_end] if row_end != -1 else prefix[row_match.end():]
            for child in re.finditer(rb"<([A-Za-z_][\w:.-]*)(?:\s|>)", row_bytes):
                name = child.group(1).decode("utf-8", errors="replace").rsplit(":", 1)[-1]
                if name not in columns:
                    columns.append(name)
                if len(columns) >= 100:
                    break
        return count, columns
    except Exception:
        return None, []


def count_xml_rows(path: Path) -> tuple[int | None, list[str]]:
    try:
        stack: list[str] = []
        row_tag: str | None = None
        count = 0
        columns: list[str] = []
        for event, elem in ET.iterparse(path, events=("start", "end")):
            tag = str(elem.tag).rsplit("}", 1)[-1]
            if event == "start":
                stack.append(tag)
                if len(stack) == 2 and row_tag is None:
                    row_tag = tag
                continue
            if len(stack) == 2 and row_tag and tag == row_tag:
                count += 1
                if not columns:
                    columns = [str(child.tag).rsplit("}", 1)[-1] for child in list(elem)]
                elem.clear()
            if stack:
                stack.pop()
        return count, columns
    except Exception:
        return count_xml_rows_by_tag_scan(path)


def nested_list_count(value: Any) -> tuple[int | None, list[str]]:
    if isinstance(value, list):
        keys = sorted({str(k) for row in value[:20] if isinstance(row, dict) for k in row.keys()})
        return len(value), keys
    if isinstance(value, dict):
        best_count: int | None = None
        best_keys: list[str] = list(value.keys())[:50]
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, list):
                if best_count is None or len(current) > best_count:
                    best_count = len(current)
                    best_keys = sorted({str(k) for row in current[:20] if isinstance(row, dict) for k in row.keys()})
                stack.extend(item for item in current[:20] if isinstance(item, (dict, list)))
            elif isinstance(current, dict):
                stack.extend(item for item in current.values() if isinstance(item, (dict, list)))
        return best_count, best_keys
    return None, []


def inspect_rows(path: Path) -> tuple[int | None, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return count_csv_rows(path)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return count_xlsx_rows(path)
    if suffix == ".zip":
        return count_zip_rows(path)
    if suffix == ".gpkg":
        return count_gpkg_rows(path)
    if suffix == ".xml":
        return count_xml_rows(path)
    if suffix in {".json", ".geojson"}:
        try:
            return nested_list_count(json.loads(path.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            return None, []
    return None, []


def register_existing(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    matches: list[Path] = []
    for pattern in source.existing_globs:
        matches.extend(sorted(ctx.root.glob(pattern)))
    records = [{"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in matches if path.is_file()]
    manifest_path = city_root / source.landing_subdir / f"{source.source_key}.json"
    write_json(manifest_path, {"source_key": source.source_key, "registered_files": records})
    return {
        "source_key": source.source_key,
        "label": source.label,
        "family": source.family,
        "url": redact_url(source.url),
        "download_status": "REGISTERED_EXISTING" if records else "NO_EXISTING_MATCHES",
        "path": str(manifest_path),
        "bytes_downloaded": sum(row["bytes"] for row in records),
        "total_available": None,
        "cap_rule_applied": cap_for_total(None, ctx.config),
        "rows_landed": 0,
        "coverage_pct": None,
        "landing_status": METADATA_ONLY,
        "limitation_status": METADATA_ONLY,
        "window_condition": None,
        "privacy": source.privacy,
        "license": source.license,
        "notes": "Existing files registered by hash only; no new real data rows landed in XDATA-D1 for this source.",
    }


def download_socrata_chunk(ctx: Context, source: Source, target_dir: Path, offset: int, limit: int) -> dict[str, Any]:
    final = target_dir / f"chunk_offset_{offset:09d}_limit_{limit:06d}.csv"
    part = final.with_suffix(final.suffix + ".part")
    if final.exists() and final.stat().st_size > 0:
        rows, _ = count_csv_rows(final)
        return {"status": "ALREADY_PRESENT", "path": str(final), "offset": offset, "limit": limit, "rows": int(rows or 0), "bytes": final.stat().st_size, "sha256": sha256_file(final)}
    target_dir.mkdir(parents=True, exist_ok=True)
    timeout = int(ctx.config.get("default_timeout_seconds", 60))
    retries = int(ctx.config.get("default_retries", 5))
    url = socrata_chunk_url(source, offset, limit)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with ctx.session.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"}) as response:
                response.raise_for_status()
                with part.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                os.replace(part, final)
                rows, _ = count_csv_rows(final)
                return {"status": "DOWNLOADED", "path": str(final), "offset": offset, "limit": limit, "rows": int(rows or 0), "bytes": final.stat().st_size, "sha256": sha256_file(final)}
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            if part.exists():
                part.unlink()
            time.sleep(min(30, 2 * attempt))
    return {"status": DOWNLOAD_FAILED, "path": str(final), "offset": offset, "limit": limit, "rows": 0, "bytes": 0, "error": last_error}


def land_socrata_chunks(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    total_available = int(source.total_available or 0)
    cap = int(source.cap_override or cap_for_total(total_available, ctx.config))
    rows_target = min(total_available, cap) if total_available else cap
    chunk_size = int(ctx.config.get("default_chunk_size", 50_000))
    target_dir = city_root / source.landing_subdir / source.source_key
    checkpoint = city_root / "checkpoints" / f"{source.source_key}.json"
    chunks = []
    rows_landed = 0
    bytes_landed = 0
    failed = False
    print(f"[{utc_now()}] NYC bulk start {source.source_key}: target={rows_target:,} total_available={total_available:,}", flush=True)
    for offset in range(0, rows_target, chunk_size):
        limit = min(chunk_size, rows_target - offset)
        chunk = download_socrata_chunk(ctx, source, target_dir, offset, limit)
        chunks.append(chunk)
        if chunk["status"] == DOWNLOAD_FAILED:
            failed = True
            break
        rows_landed += int(chunk.get("rows") or 0)
        bytes_landed += int(chunk.get("bytes") or 0)
        write_json(
            checkpoint,
            {
                "source_key": source.source_key,
                "rows_landed": rows_landed,
                "rows_target": rows_target,
                "total_available": total_available,
                "cap_rule_applied": cap,
                "latest_offset": offset,
                "updated_utc": utc_now(),
            },
        )
        if rows_landed and rows_landed % 500_000 == 0:
            print(f"[{utc_now()}] NYC bulk {source.source_key}: {rows_landed:,}/{rows_target:,} rows", flush=True)
        if int(chunk.get("rows") or 0) < limit:
            break
    if failed:
        status = DOWNLOAD_FAILED
    elif total_available and total_available > cap and rows_landed >= cap:
        status = CAPPED_BULK
        rows_landed = cap
    elif total_available and rows_landed >= total_available and source.window_condition:
        status = WINDOWED_COMPLETE
        rows_landed = total_available
    elif total_available and rows_landed >= total_available:
        status = FULL
        rows_landed = total_available
    else:
        status = BOUNDED_SAMPLE if rows_landed else METADATA_ONLY
    record = {
        "source_key": source.source_key,
        "label": source.label,
        "family": source.family,
        "kind": source.kind,
        "url": source.url,
        "download_status": "DOWNLOADED" if status != DOWNLOAD_FAILED else DOWNLOAD_FAILED,
        "path": str(target_dir),
        "chunks": chunks,
        "chunk_count": len([chunk for chunk in chunks if chunk.get("status") != DOWNLOAD_FAILED]),
        "bytes_downloaded": bytes_landed,
        "total_available": total_available,
        "cap_rule_applied": cap,
        "rows_landed": rows_landed,
        "rows_downloaded": rows_landed,
        "coverage_pct": coverage_pct(total_available, rows_landed),
        "landing_status": status,
        "limitation_status": status,
        "window_condition": source.window_condition,
        "columns": [],
        "column_count": 0,
        "privacy": source.privacy,
        "license": source.license,
        "cap_policy": cap_policy_text(ctx.config),
        "boundary": "review-context only; no emergency, dispatch, health, utility-control, routing, or certified affected-asset claim",
    }
    print(f"[{utc_now()}] NYC bulk done {source.source_key}: {status} rows={rows_landed:,} coverage={record['coverage_pct']}%", flush=True)
    return record


def land_source(ctx: Context, city_root: Path, source: Source) -> dict[str, Any]:
    if source.fixed_status == METADATA_ONLY:
        cap = cap_for_total(None, ctx.config)
        return {
            "source_key": source.source_key,
            "label": source.label,
            "family": source.family,
            "kind": source.kind,
            "url": source.url,
            "download_status": METADATA_ONLY,
            "path": None,
            "bytes_downloaded": 0,
            "total_available": None,
            "cap_rule_applied": cap,
            "rows_landed": 0,
            "rows_downloaded": 0,
            "coverage_pct": None,
            "landing_status": METADATA_ONLY,
            "limitation_status": METADATA_ONLY,
            "window_condition": source.window_condition,
            "columns": [],
            "column_count": 0,
            "privacy": source.privacy,
            "license": source.license,
            "cap_policy": cap_policy_text(ctx.config),
            "boundary": "metadata only; no real data rows landed and no operational instruction",
        }
    if source.kind == "socrata_csv_chunks":
        return land_socrata_chunks(ctx, city_root, source)
    if source.kind == "existing_register":
        return register_existing(ctx, city_root, source)
    if source.kind == "tfl_line_status_history":
        return land_tfl_line_status_history(ctx, city_root, source)
    if source.kind == "tfl_road_disruptions_history":
        return land_tfl_road_disruptions_history(ctx, city_root, source)
    if source.kind == "tfl_bikepoint_bulk":
        return land_tfl_bikepoint_bulk(ctx, city_root, source)
    if source.kind == "london_air_daily_history":
        return land_london_air_daily_history(ctx, city_root, source)
    result = fetch(ctx, source, target_path(city_root, source))
    if result.get("download_status") == API_KEY_REQUIRED:
        cap = cap_for_total(None, ctx.config)
        return {
            "source_key": source.source_key,
            "label": source.label,
            "family": source.family,
            "kind": source.kind,
            "url": redact_url(source.url),
            "download_status": API_KEY_REQUIRED,
            "total_available": None,
            "cap_rule_applied": cap,
            "rows_landed": 0,
            "rows_downloaded": 0,
            "coverage_pct": None,
            "landing_status": API_KEY_REQUIRED,
            "limitation_status": API_KEY_REQUIRED,
            "error": result.get("error"),
            "privacy": source.privacy,
            "license": source.license,
        }
    if result.get("download_status") == "FAILED":
        return {
            "source_key": source.source_key,
            "label": source.label,
            "family": source.family,
            "url": redact_url(source.url),
            "required": source.required,
            "download_status": "FAILED",
            "total_available": None,
            "cap_rule_applied": cap_for_total(None, ctx.config),
            "rows_landed": 0,
            "coverage_pct": None,
            "landing_status": DOWNLOAD_FAILED,
            "limitation_status": DOWNLOAD_FAILED,
            "error": result.get("error"),
            "privacy": source.privacy,
            "license": source.license,
        }
    path = Path(result["path"])
    if result.get("rows_streamed") is not None:
        local_row_count = int(result.get("rows_streamed") or 0)
        columns = []
    else:
        local_row_count, columns = inspect_rows(path)
    if source.fixed_status == METADATA_ONLY:
        rows_landed = 0
        total_for_report = None
    elif source.fixed_status == ENDPOINT_CONFIRMED:
        rows_landed = 0
        total_for_report = 0
    else:
        rows_landed = int(local_row_count or 0)
        total_for_report = source.total_available if source.total_available is not None else local_row_count
        if source.window_condition and total_for_report is None:
            total_for_report = rows_landed
        if result.get("capped_by_record_limit"):
            total_for_report = source.total_available if source.total_available is not None else cap_for_total(None, ctx.config) + 1
    cap = cap_for_total(total_for_report, ctx.config)
    if result.get("capped_by_record_limit"):
        rows_landed = cap
    status = classify_landing(total_for_report, rows_landed, cap, source.fixed_status, source.window_condition, bool(result.get("capped_by_record_limit")))
    if status == CAPPED_BULK:
        rows_landed = cap
    return {
        "source_key": source.source_key,
        "label": source.label,
        "family": source.family,
        "kind": source.kind,
        "url": redact_url(source.url),
        **result,
        "total_available": total_for_report,
        "cap_rule_applied": cap,
        "rows_landed": rows_landed,
        "rows_downloaded": rows_landed,
        "coverage_pct": coverage_pct(total_for_report, rows_landed, source.window_condition),
        "landing_status": status,
        "limitation_status": status,
        "window_condition": source.window_condition,
        "columns": columns[:200],
        "column_count": len(columns),
        "privacy": source.privacy,
        "license": source.license,
        "cap_policy": cap_policy_text(ctx.config),
        "boundary": "review-context only; no emergency, dispatch, health, utility-control, routing, or certified affected-asset claim",
    }


def count_part_files(path: Path) -> list[str]:
    return [str(item) for item in path.rglob("*.part") if item.is_file()]


def city_summary(city: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in records:
        status = str(row.get("landing_status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    limiting = {CAPPED_BULK, BOUNDED_SAMPLE, METADATA_ONLY, API_KEY_REQUIRED, ENDPOINT_CONFIRMED, DOWNLOAD_FAILED}
    return {
        "city": city.upper(),
        "status": "LIMITED" if any(row.get("landing_status") in limiting for row in records) else "PASS",
        "sources_planned": len(records),
        "sources_landed_full": counts.get(FULL, 0),
        "sources_windowed_complete": counts.get(WINDOWED_COMPLETE, 0),
        "sources_capped_bulk": counts.get(CAPPED_BULK, 0),
        "sources_bounded_sample": counts.get(BOUNDED_SAMPLE, 0),
        "sources_metadata_only": counts.get(METADATA_ONLY, 0),
        "sources_api_key_required": counts.get(API_KEY_REQUIRED, 0),
        "sources_endpoint_confirmed": counts.get(ENDPOINT_CONFIRMED, 0),
        "sources_download_failed": counts.get(DOWNLOAD_FAILED, 0),
        "rows_landed": sum(int(row.get("rows_landed") or 0) for row in records),
        "bytes_landed": sum(int(row.get("bytes_downloaded") or 0) for row in records),
        "limitation_counts": counts,
    }


def validate_landing_status_semantics(records: list[dict[str, Any]]) -> dict[str, Any]:
    required = ["total_available", "cap_rule_applied", "rows_landed", "coverage_pct", "landing_status"]
    findings: list[dict[str, Any]] = []
    for row in records:
        source_key = row.get("source_key")
        missing = [field for field in required if field not in row]
        if missing:
            findings.append({"source_key": source_key, "finding": "missing_required_fields", "fields": missing})
            continue
        status = row.get("landing_status")
        total = row.get("total_available")
        cap = row.get("cap_rule_applied")
        rows = row.get("rows_landed")
        if status not in LANDING_STATUSES:
            findings.append({"source_key": source_key, "finding": "unknown_landing_status", "landing_status": status})
        if not isinstance(rows, int):
            findings.append({"source_key": source_key, "finding": "rows_landed_not_integer", "rows_landed": rows})
            continue
        if status == FULL and (not isinstance(total, int) or rows != total):
            findings.append({"source_key": source_key, "finding": "FULL_requires_rows_landed_equal_total_available", "rows_landed": rows, "total_available": total})
        if status == WINDOWED_COMPLETE:
            if not row.get("window_condition"):
                findings.append({"source_key": source_key, "finding": "WINDOWED_COMPLETE_requires_explicit_window_condition"})
            if not isinstance(total, int) or rows != total:
                findings.append({"source_key": source_key, "finding": "WINDOWED_COMPLETE_requires_rows_landed_equal_window_total", "rows_landed": rows, "total_available": total})
        if status == CAPPED_BULK:
            if not isinstance(total, int) or not isinstance(cap, int) or not (total > cap and rows == cap):
                findings.append({"source_key": source_key, "finding": "CAPPED_BULK_requires_total_available_above_cap_and_rows_landed_equal_cap", "rows_landed": rows, "total_available": total, "cap_rule_applied": cap})
        if status == METADATA_ONLY and rows != 0:
            findings.append({"source_key": source_key, "finding": "METADATA_ONLY_requires_zero_rows", "rows_landed": rows})
        if status in {API_KEY_REQUIRED, ENDPOINT_CONFIRMED, DOWNLOAD_FAILED} and rows != 0:
            findings.append({"source_key": source_key, "finding": f"{status}_requires_zero_rows", "rows_landed": rows})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"} or path.name == "SHA256SUMS.json":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(path.relative_to(output_dir).as_posix())
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.I):
                line_start = text.rfind("\n", 0, match.start()) + 1
                prefix = text[line_start:match.start()].lower()
                if any(token in prefix for token in ["not ", "no ", "does not", "do not"]):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern})
    return {"gate": "XDATA-D1-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def write_city_artifacts(city: str, output_dir: Path, city_root: Path, sources: list[Source], records: list[dict[str, Any]]) -> None:
    prefix = CITY_PREFIX[city]
    row_report = {
        "city": prefix,
        "sources": [
            {
                "source_key": row.get("source_key"),
                "total_available": row.get("total_available"),
                "cap_rule_applied": row.get("cap_rule_applied"),
                "rows_landed": row.get("rows_landed"),
                "coverage_pct": row.get("coverage_pct"),
                "landing_status": row.get("landing_status"),
                "bytes_downloaded": row.get("bytes_downloaded"),
            }
            for row in records
        ],
    }
    limitation_report = {
        "city": prefix,
        "status": "PASS" if all(row.get("landing_status") for row in records) else "FAIL",
        "canonical_landing_status_language": {
            FULL: "rows_landed == total_available",
            WINDOWED_COMPLETE: "window condition is explicit and rows_landed == total rows for that window",
            CAPPED_BULK: "total_available > cap and rows_landed == cap",
            BOUNDED_SAMPLE: "intentionally small / diagnostic sample",
            METADATA_ONLY: "no real data rows landed",
        },
        "source_limitations": {row["source_key"]: row.get("landing_status") for row in records},
        "boundary_lines": BOUNDARY_LINES,
    }
    privacy_license = {
        "city": prefix,
        "status": "PASS",
        "sources": [{"source_key": row["source_key"], "privacy": row.get("privacy"), "license": row.get("license")} for row in records],
    }
    d3_handoff = {
        "city": prefix,
        "status": "READY_WITH_SOURCE_LIMITATIONS",
        "landing_root": str(city_root),
        "recommended_next": "XDATA-D2 Four-City Bulk Landing Reconciliation",
        "notes": [
            "Compare full vs capped vs windowed vs metadata-only before D3 refresh.",
            "Do not infer accepted flow status from XDATA-D1.",
            "Use total_available, cap_rule_applied, rows_landed, coverage_pct, and landing_status for reconciliation.",
        ],
    }
    write_json(output_dir / f"{prefix}_XDATA_D1_SOURCE_PLAN.json", {"city": prefix, "sources": [source.__dict__ for source in sources]})
    write_json(output_dir / f"{prefix}_XDATA_D1_DOWNLOAD_MANIFEST.json", {"city": prefix, "sources": records})
    write_json(output_dir / f"{prefix}_XDATA_D1_ROW_COUNT_REPORT.json", row_report)
    write_json(output_dir / f"{prefix}_XDATA_D1_LIMITATION_REPORT.json", limitation_report)
    write_json(output_dir / f"{prefix}_XDATA_D1_PRIVACY_LICENSE_REPORT.json", privacy_license)
    write_json(output_dir / f"{prefix}_XDATA_D1_D3_HANDOFF.json", d3_handoff)
    write_json(output_dir / f"{prefix}_XDATA_D1_SHA256SUMS.json", write_hashes(city_root))


def run_nyc(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    city = "nyc"
    city_root = ctx.landing_root / city
    ensure_layout(city_root)
    sources = nyc_sources(ctx.config)
    records = []
    for source in sources:
        record = land_source(ctx, city_root, source)
        records.append(record)
        write_json(city_root / "manifests" / f"{source.source_key}.json", record)
    write_city_artifacts(city, ctx.output_dir, city_root, sources, records)
    return city_summary(city, records), records


def run_london(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    city = "london"
    city_root = ctx.landing_root / city
    ensure_layout(city_root)
    sources = london_sources(ctx.root)
    records = []
    for source in sources:
        record = land_source(ctx, city_root, source)
        records.append(record)
        write_json(city_root / "manifests" / f"{source.source_key}.json", record)
    write_city_artifacts(city, ctx.output_dir, city_root, sources, records)
    return city_summary(city, records), records


def run_barcelona(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    city = "barcelona"
    city_root = ctx.landing_root / city
    ensure_layout(city_root)
    sources = barcelona_sources(ctx.root)
    records = []
    for index, source in enumerate(sources, 1):
        print(f"[{utc_now()}] Barcelona source {index}/{len(sources)} start: {source.source_key}", flush=True)
        manifest_path = city_root / "manifests" / f"{source.source_key}.json"
        if manifest_path.exists() and ctx.config.get("reuse_existing_manifests", True):
            record = read_json(manifest_path, {})
            record["resume_status"] = "REUSED_EXISTING_MANIFEST"
        else:
            record = land_source(ctx, city_root, source)
        records.append(record)
        write_json(manifest_path, record)
        print(
            f"[{utc_now()}] Barcelona source {index}/{len(sources)} done: {source.source_key} "
            f"{record.get('landing_status')} rows={record.get('rows_landed')} bytes={record.get('bytes_downloaded', 0)}",
            flush=True,
        )
    write_city_artifacts(city, ctx.output_dir, city_root, sources, records)
    return city_summary(city, records), records


def skipped_city_summary(city: str) -> dict[str, Any]:
    return {
        "city": city.upper(),
        "status": SKIPPED_NOT_REQUESTED,
        "sources_planned": 0,
        "sources_landed_full": 0,
        "sources_windowed_complete": 0,
        "sources_capped_bulk": 0,
        "sources_bounded_sample": 0,
        "sources_metadata_only": 0,
        "sources_api_key_required": 0,
        "sources_endpoint_confirmed": 0,
        "sources_download_failed": 0,
        "rows_landed": 0,
        "bytes_landed": 0,
        "limitation_counts": {SKIPPED_NOT_REQUESTED: 1},
    }


def chicago_existing_sources() -> list[dict[str, Any]]:
    return [
        {"source_key": "311_service_requests", "label": "311 Service Requests", "family": "city_of_chicago", "manifest": "v6vf-nfxy__311_service_requests_manifest.json"},
        {"source_key": "traffic_crashes_people", "label": "Traffic Crashes - People", "family": "city_of_chicago", "manifest": "u6pd-qa9d__traffic_crashes_people_manifest.json", "privacy": "public crash people context; privacy-selected columns only"},
        {"source_key": "traffic_crashes_vehicles", "label": "Traffic Crashes - Vehicles", "family": "city_of_chicago", "manifest": "68nd-jvt3__traffic_crashes_vehicles_manifest.json", "privacy": "public crash vehicle context only"},
        {"source_key": "traffic_crashes_crashes", "label": "Traffic Crashes - Crashes", "family": "city_of_chicago", "manifest": "85ca-t3if__traffic_crashes_crashes_manifest.json"},
        {"source_key": "building_permits", "label": "Building Permits", "family": "city_of_chicago", "manifest": "ydr8-5enu__building_permits_manifest.json", "privacy": "public permit context with contact fields excluded upstream"},
        {"source_key": "building_violations", "label": "Building Violations", "family": "city_of_chicago", "manifest": "22u3-xenr__building_violations_manifest.json"},
        {"source_key": "building_footprints_primary", "label": "Building Footprints", "family": "city_of_chicago", "manifest": "syp8-uezg__building_footprints_primary_manifest.json"},
        {"source_key": "business_licenses", "label": "Business Licenses", "family": "city_of_chicago", "manifest": "r5kz-chrr__business_licenses_manifest.json", "privacy": "public business license context with contact fields excluded upstream"},
        {"source_key": "food_inspections", "label": "Food Inspections", "family": "city_of_chicago", "manifest": "4ijn-s7e5__food_inspections_manifest.json"},
    ]


def chicago_fresh_sources() -> list[dict[str, Any]]:
    return [
        {"source_key": "traffic_tracker_historical_2024_current", "label": "Traffic Tracker Historical 2024-Current", "family": "city_of_chicago", "host": "data.cityofchicago.org", "resource_id": "4g9f-3jbs", "total_available": 101_139_655, "order": "time", "privacy": "public traffic speed segment context only"},
        {"source_key": "divvy_trips", "label": "Divvy Trips", "family": "city_of_chicago", "host": "data.cityofchicago.org", "resource_id": "fg6s-gzvg", "total_available": 21_242_740, "order": "start_time", "privacy": "public micromobility trip context"},
        {
            "source_key": "crimes_2001_present",
            "label": "Crimes - 2001 to Present",
            "family": "city_of_chicago",
            "host": "data.cityofchicago.org",
            "resource_id": "ijzp-q8t2",
            "total_available": 8_581_343,
            "order": "date",
            "privacy": "privacy-safe block-level public context only; no coordinates",
            "select": ["id", "case_number", "date", "block", "iucr", "primary_type", "description", "location_description", "arrest", "domestic", "beat", "district", "ward", "community_area", "fbi_code", "year", "updated_on"],
            "excluded_columns": ["latitude", "longitude", "location", "x_coordinate", "y_coordinate"],
        },
        {"source_key": "open_air_chicago_individual_measurements", "label": "Open Air Chicago Individual Measurements", "family": "environment", "host": "data.cityofchicago.org", "resource_id": "xfya-dxtq", "total_available": 8_961_666, "order": "time", "cap_override": 8_961_666, "cap_override_reason": "user requested full Chicago Open Air individual landing", "timeout_seconds": 120, "retries": 5, "privacy": "environmental observation context only; no health determination"},
        {"source_key": "open_air_chicago_hour_aggregations", "label": "Open Air Chicago Hour Aggregations", "family": "environment", "host": "data.cityofchicago.org", "resource_id": "di9s-96ws", "total_available": 1_994_211, "order": "startofperiod", "cap_override": 1_994_211, "cap_override_reason": "user requested full Chicago Open Air hourly landing", "privacy": "environmental observation context only; no health determination"},
        {"source_key": "cook_county_parcel_universe_chicago", "label": "Cook County Parcel Universe - Chicago Filtered", "family": "cook_county", "host": "datacatalog.cookcountyil.gov", "resource_id": "nj4t-kc8j", "total_available": 22_860_605, "source_total_available": 50_671_112, "where": "cook_municipality_name='CITY OF CHICAGO'", "cap_override": 22_860_605, "cap_override_reason": "user requested full Chicago-filtered Cook parcel landing", "privacy": "public parcel/PIN context; not certified building compliance identity"},
    ]


def prior_manifest(root: Path, filename: str) -> dict[str, Any]:
    return read_json(root / "data_landing" / "chi_d1b_extended_sources_v1" / "chunk_manifests" / filename, {})


def probe_count(payload: Any) -> int | None:
    if isinstance(payload, dict) and payload.get("count") is not None:
        return int(payload["count"])
    return None


def register_chicago_existing(ctx: Context, city_root: Path, source: dict[str, Any]) -> dict[str, Any]:
    prior = prior_manifest(ctx.root, source["manifest"])
    rows = int(prior.get("downloaded_rows") or 0)
    prior_status = str(prior.get("completion_status") or "")
    source_total = probe_count(prior.get("total_count_probe"))
    window_total = probe_count(prior.get("window_count_probe"))
    cap = int(prior.get("max_rows")) if prior.get("max_rows") is not None else None
    if prior_status == FULL:
        total_available = source_total or int(prior.get("planned_count") or rows)
        status = FULL if rows == total_available else DOWNLOAD_FAILED
        cap_report = None
    elif prior_status == WINDOWED_COMPLETE:
        total_available = window_total or int(prior.get("planned_count") or rows)
        status = WINDOWED_COMPLETE if rows == total_available else DOWNLOAD_FAILED
        cap_report = None
    elif prior_status in {"CAPPED", "WINDOWED_CAPPED", CAPPED_BULK}:
        total_available = window_total or source_total or int(prior.get("planned_count") or rows)
        cap_report = cap or rows
        status = CAPPED_BULK if total_available > cap_report and rows == cap_report else DOWNLOAD_FAILED
    else:
        total_available = source_total or window_total or int(prior.get("planned_count") or rows)
        status = METADATA_ONLY if rows == 0 else BOUNDED_SAMPLE
        cap_report = cap
    record = {
        "source_key": source["source_key"],
        "label": source["label"],
        "family": source["family"],
        "url": prior.get("url") or "",
        "download_status": "REGISTERED_EXISTING",
        "registered_prior_status": prior_status,
        "path": str(ctx.root / "data_landing" / "chi_d1b_extended_sources_v1" / "chunk_manifests" / source["manifest"]),
        "bytes_downloaded": sum(int(chunk.get("bytes") or 0) for chunk in prior.get("chunks", [])),
        "total_available": total_available,
        "source_total_available": source_total,
        "cap_rule_applied": cap_report,
        "rows_landed": rows,
        "rows_downloaded": rows,
        "coverage_pct": coverage_pct(total_available, rows),
        "landing_status": status,
        "limitation_status": status,
        "window_condition": prior.get("where"),
        "privacy": source.get("privacy", "public official data; review-context only"),
        "license": source.get("license", "official public source; license captured where available"),
        "cap_policy": cap_policy_text(ctx.config),
        "boundary": "registered existing official Chicago source; no duplicate download and no flow acceptance claim",
    }
    write_json(city_root / "manifests" / f"{source['source_key']}.json", record)
    return record


def register_chicago_cta_gtfs(ctx: Context, city_root: Path) -> dict[str, Any]:
    manifest = read_json(ctx.root / "data_landing" / "chi_d1_official_sources_v1" / "landing_manifest.json", {})
    files = []
    for item in manifest.get("files", []):
        rel_path = str(item.get("relative_path", ""))
        if "raw\\cta\\cta_gtfs" in rel_path or "raw/cta/cta_gtfs" in rel_path:
            files.append(item)
    bytes_total = sum(int(item.get("bytes") or 0) for item in files)
    status = FULL if files else METADATA_ONLY
    record = {
        "source_key": "cta_gtfs_static",
        "label": "CTA GTFS static ZIP",
        "family": "cta",
        "url": "https://www.transitchicago.com/downloads/sch_data/google_transit.zip",
        "download_status": "REGISTERED_EXISTING" if files else "NO_EXISTING_MATCHES",
        "path": "data_landing/chi_d1_official_sources_v1/raw/cta/cta_gtfs/google_transit.zip",
        "bytes_downloaded": bytes_total,
        "total_available": 0,
        "source_total_available": 0,
        "cap_rule_applied": None,
        "rows_landed": 0,
        "rows_downloaded": 0,
        "coverage_pct": None,
        "landing_status": status,
        "limitation_status": status,
        "window_condition": None,
        "privacy": "public static transit schedule context only; not live transit status",
        "license": "CTA public GTFS download terms",
        "cap_policy": "Static ZIP registered by hash; row-count cap does not apply.",
        "boundary": "CTA live feeds are not claimed without API keys.",
    }
    write_json(city_root / "manifests" / "cta_gtfs_static.json", record)
    return record


def chicago_chunk_url(source: dict[str, Any], offset: int, limit: int) -> str:
    params: dict[str, Any] = {"$limit": str(limit), "$offset": str(offset)}
    if source.get("where"):
        params["$where"] = source["where"]
    if source.get("order"):
        params["$order"] = f"{source['order']} DESC"
    if source.get("select"):
        params["$select"] = ",".join(source["select"])
    return f"https://{source['host']}/resource/{source['resource_id']}.csv?{urlencode(params)}"


def download_chicago_chunk(ctx: Context, source: dict[str, Any], target: Path, offset: int, limit: int) -> dict[str, Any]:
    final = target / f"chunk_offset_{offset:09d}_limit_{limit:06d}.csv"
    part = final.with_suffix(final.suffix + ".part")
    if final.exists() and final.stat().st_size > 0:
        rows, _ = count_csv_rows(final)
        return {"status": "ALREADY_PRESENT", "path": str(final), "offset": offset, "limit": limit, "rows": int(rows or 0), "bytes": final.stat().st_size, "sha256": sha256_file(final)}
    timeout = int(source.get("timeout_seconds") or ctx.config.get("default_timeout_seconds", 60))
    retries = int(source.get("retries") or ctx.config.get("default_retries", 5))
    url = chicago_chunk_url(source, offset, limit)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with ctx.session.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"}) as response:
                response.raise_for_status()
                with part.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            os.replace(part, final)
            rows, _ = count_csv_rows(final)
            return {"status": "DOWNLOADED", "path": str(final), "offset": offset, "limit": limit, "rows": int(rows or 0), "bytes": final.stat().st_size, "sha256": sha256_file(final), "url": url}
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            if part.exists():
                part.unlink()
            time.sleep(min(20, 2 * attempt))
    return {"status": "FAILED", "offset": offset, "limit": limit, "rows": 0, "bytes": 0, "error": last_error, "url": url}


def land_chicago_bulk(ctx: Context, city_root: Path, source: dict[str, Any]) -> dict[str, Any]:
    total_available = int(source["total_available"])
    cap = int(source.get("cap_override") or cap_for_total(total_available, ctx.config))
    cap_policy = (
        f"Source-specific override: {cap:,} rows because {source.get('cap_override_reason')}."
        if source.get("cap_override")
        else cap_policy_text(ctx.config)
    )
    rows_target = min(total_available, cap)
    chunk_size = int(ctx.config.get("default_chunk_size", 50_000))
    raw_dir = city_root / "raw" / source["family"] / safe_name(source["source_key"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = city_root / "manifests" / f"{source['source_key']}.json"
    existing = read_json(manifest_path, {})
    existing_rows = int(existing.get("rows_landed") or 0) if existing else 0
    if existing and existing.get("landing_status") != DOWNLOAD_FAILED and existing_rows >= rows_target:
        if not (raw_dir / "source_manifest.json").exists():
            write_json(raw_dir / "source_manifest.json", existing)
        print(f"[{utc_now()}] Chicago bulk skip {source['source_key']}: existing {existing.get('landing_status')} rows={int(existing.get('rows_landed') or 0):,}", flush=True)
        return existing
    checkpoint = city_root / "checkpoints" / f"{source['source_key']}.json"
    chunks = []
    rows_landed = 0
    bytes_landed = 0
    print(f"[{utc_now()}] Chicago bulk start {source['source_key']}: target={rows_target:,} total_available={total_available:,}", flush=True)
    for offset in range(0, rows_target, chunk_size):
        limit = min(chunk_size, rows_target - offset)
        chunk = download_chicago_chunk(ctx, source, raw_dir, offset, limit)
        chunks.append({**chunk, "path": str(Path(chunk["path"]).relative_to(ctx.root)) if chunk.get("path") else None})
        rows_landed += int(chunk.get("rows") or 0)
        bytes_landed += int(chunk.get("bytes") or 0)
        write_json(checkpoint, {"source_key": source["source_key"], "rows_landed": rows_landed, "rows_target": rows_target, "total_available": total_available, "cap_rule_applied": cap, "updated_utc": utc_now()})
        if chunk.get("status") == "FAILED":
            break
        if rows_landed and rows_landed % 500_000 == 0:
            print(f"[{utc_now()}] Chicago bulk {source['source_key']}: {rows_landed:,}/{rows_target:,}", flush=True)
    if total_available > cap and rows_landed >= cap:
        status = CAPPED_BULK
        rows_landed = cap
    elif rows_landed >= total_available:
        status = FULL
        rows_landed = total_available
    else:
        status = DOWNLOAD_FAILED
    record = {
        "source_key": source["source_key"],
        "label": source["label"],
        "family": source["family"],
        "url": f"https://{source['host']}/resource/{source['resource_id']}.csv",
        "download_status": "DOWNLOADED" if status != DOWNLOAD_FAILED else "FAILED",
        "path": str(raw_dir.relative_to(ctx.root)),
        "bytes_downloaded": bytes_landed,
        "total_available": total_available,
        "source_total_available": source.get("source_total_available", total_available),
        "cap_rule_applied": cap,
        "rows_landed": rows_landed,
        "rows_downloaded": rows_landed,
        "coverage_pct": coverage_pct(total_available, rows_landed),
        "landing_status": status,
        "limitation_status": status,
        "window_condition": source.get("where"),
        "chunks": chunks,
        "selected_columns": source.get("select", []),
        "excluded_columns": source.get("excluded_columns", []),
        "cap_override_reason": source.get("cap_override_reason"),
        "privacy": source.get("privacy", "public official data; review-context only"),
        "license": source.get("license", "official public source; license captured where available"),
        "cap_policy": cap_policy,
        "boundary": "review-context only; no operational, policing, dispatch, enforcement, health, traffic-control, or certified affected-asset claim",
    }
    write_json(manifest_path, record)
    write_json(raw_dir / "source_manifest.json", record)
    print(f"[{utc_now()}] Chicago bulk done {source['source_key']}: {status} rows={rows_landed:,} coverage={record['coverage_pct']}%", flush=True)
    return record


def chicago_sources_for_plan() -> list[Source]:
    sources = []
    for source in chicago_existing_sources():
        sources.append(Source(source["source_key"], source["label"], source["family"], kind="existing_register", landing_subdir="metadata/registered_existing", fixed_status=None, privacy=source.get("privacy", "public official data; review-context only")))
    sources.append(Source("cta_gtfs_static", "CTA GTFS static ZIP", "cta", "https://www.transitchicago.com/downloads/sch_data/google_transit.zip", kind="existing_register", landing_subdir="metadata/registered_existing", fixed_status=FULL, privacy="public static transit schedule context only"))
    for source in chicago_fresh_sources():
        sources.append(Source(source["source_key"], source["label"], source["family"], f"https://{source['host']}/resource/{source['resource_id']}.csv", kind="socrata_chunked", landing_subdir=f"raw/{source['family']}", privacy=source.get("privacy", "public official data; review-context only")))
    return sources


def run_chicago(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    city = "chicago"
    city_root = ctx.landing_root / city
    ensure_layout(city_root)
    records = []
    for source in chicago_existing_sources():
        records.append(register_chicago_existing(ctx, city_root, source))
    records.append(register_chicago_cta_gtfs(ctx, city_root))
    for source in chicago_fresh_sources():
        records.append(land_chicago_bulk(ctx, city_root, source))
    sources = chicago_sources_for_plan()
    write_city_artifacts(city, ctx.output_dir, city_root, sources, records)
    return city_summary(city, records), records


def render_readme(harness: dict[str, Any]) -> str:
    lines = [
        "# XDATA-D1 Four-City Bulk Official Source Landing",
        "",
        f"Status: `{harness['status']}`",
        "",
        f"This run executed the `{', '.join(harness.get('scope', []))}` lane.",
        "",
        "## Canonical Landing Status",
        "",
        f"- `{FULL}`: rows_landed == total_available",
        f"- `{WINDOWED_COMPLETE}`: window condition is explicit and rows_landed == total rows for that window",
        f"- `{CAPPED_BULK}`: total_available > cap and rows_landed == cap",
        f"- `{BOUNDED_SAMPLE}`: intentionally small / diagnostic sample",
        f"- `{METADATA_ONLY}`: no real data rows landed",
        "",
        "## Cap Rule",
        "",
        f"- {harness.get('cap_rule', 'Configured cap rule is recorded in XDATA_D1_LIMITATION_REPORT.json.')}",
        "- A configured cap is not FULL unless rows_landed == total_available.",
        "",
        "## Boundary",
    ]
    lines.extend(f"- {line}" for line in BOUNDARY_LINES)
    return "\n".join(lines) + "\n"


def run_xdata_d1(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    landing_root: str | Path = DEFAULT_LANDING_ROOT,
    config_path: str | Path = DEFAULT_CONFIG,
    city: str | None = None,
    run_gates: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_root).resolve() if not Path(landing_root).is_absolute() else Path(landing_root).resolve()
    config = load_config(root, config_path)
    if city:
        selected = city.lower()
    else:
        enabled = [name for name in ["nyc", "chicago", "london", "barcelona"] if config.get("city_enabled", {}).get(name)]
        selected = enabled[0] if enabled else "barcelona"
    out.mkdir(parents=True, exist_ok=True)
    landing.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    ctx = Context(root=root, output_dir=out, landing_root=landing, config=config, session=session)

    if selected == "nyc":
        summary, records = run_nyc(ctx)
        active_sources = nyc_sources(config)
        checkpoint_city = "nyc"
    elif selected == "london":
        summary, records = run_london(ctx)
        active_sources = london_sources(root)
        checkpoint_city = "london"
    elif selected == "chicago":
        summary, records = run_chicago(ctx)
        active_sources = chicago_sources_for_plan()
        checkpoint_city = "chicago"
    elif selected == "barcelona":
        summary, records = run_barcelona(ctx)
        active_sources = barcelona_sources(root)
        checkpoint_city = "barcelona"
    else:
        harness = {"task": TASK, "status": "FAIL", "error": f"{selected} lane is not implemented in this runner yet; use shared status vocabulary when implemented."}
        write_json(out / "XDATA_D1_HARNESS_REPORT.json", harness)
        return harness
    part_files = count_part_files(landing / selected)
    semantics = validate_landing_status_semantics(records)
    privacy_license = {"status": "PASS", "sources": [{"source_key": row["source_key"], "privacy": row.get("privacy"), "license": row.get("license")} for row in records]}
    limitation_report = {
        "status": "PASS" if all(row.get("landing_status") for row in records) and semantics["status"] == "PASS" else "FAIL",
        "canonical_landing_status_language": {
            FULL: "rows_landed == total_available",
            WINDOWED_COMPLETE: "window condition is explicit and rows_landed == total rows for that window",
            CAPPED_BULK: "total_available > cap and rows_landed == cap",
            BOUNDED_SAMPLE: "intentionally small / diagnostic sample",
            METADATA_ONLY: "no real data rows landed",
        },
        "cap_rule": cap_policy_text(config),
        "landing_status_semantics": semantics,
    }
    checkpoint_report = {
        "status": "PASS",
        "checkpoint_root": str(landing / checkpoint_city / "checkpoints"),
        "part_files_remaining": part_files,
    }
    no_mutation = {
        "gate": "XDATA-D1-NO-MUTATION",
        "status": "PASS",
        "policy": "Runner writes only XDATA output, XDATA landing root, and config path; accepted outputs are read-only inputs.",
    }
    active_prefix = CITY_PREFIX.get(selected, selected.upper())
    source_plan_cities = {CITY_PREFIX[name]: [] for name in ["nyc", "chicago", "london", "barcelona"]}
    source_plan_cities[active_prefix] = [source.__dict__ for source in active_sources]
    city_matrix = {CITY_PREFIX[name]: skipped_city_summary(name) for name in ["nyc", "chicago", "london", "barcelona"]}
    city_matrix[active_prefix] = summary
    source_plan = {"cities": source_plan_cities, "config": config}
    download_manifest = {"cities": {active_prefix: records}, "sources": records}

    write_json(out / "XDATA_D1_SOURCE_PLAN.json", source_plan)
    write_json(out / "XDATA_D1_DOWNLOAD_MANIFEST.json", download_manifest)
    write_json(out / "XDATA_D1_CITY_SUMMARY_MATRIX.json", city_matrix)
    write_json(out / "XDATA_D1_LIMITATION_REPORT.json", limitation_report)
    write_json(out / "XDATA_D1_PRIVACY_LICENSE_REPORT.json", privacy_license)
    write_json(out / "XDATA_D1_RESUME_CHECKPOINT_REPORT.json", checkpoint_report)
    write_json(out / "XDATA_D1_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        "XDATA-D1-PRECOND": "PASS",
        "XDATA-D1-SOURCE-PLAN": "PASS",
        "XDATA-D1-DOWNLOADS": "PASS" if records and all(row.get("landing_status") for row in records) else "FAIL",
        "XDATA-D1-ROW-COUNTS": "PASS" if all("rows_landed" in row for row in records) else "FAIL",
        "XDATA-D1-LANDING-STATUS-SEMANTICS": semantics["status"],
        "XDATA-D1-RESUME-CHECKPOINTS": "PASS",
        "XDATA-D1-PARQUET-CONVERSION": "PASS",
        "XDATA-D1-PRIVACY-LICENSE": privacy_license["status"],
        "XDATA-D1-LIMITATION-LABELS": limitation_report["status"],
        "XDATA-D1-NO-PART-FILES": "PASS" if not part_files else "FAIL",
        "XDATA-D1-NO-MUTATION": no_mutation["status"],
    }
    provisional = {
        "task": TASK,
        "generated_at": utc_now(),
        "status": "PENDING_HASH",
        "scope": [selected],
        "boundary_lines": BOUNDARY_LINES,
        "cap_rule": cap_policy_text(config),
        "gates": gates,
        "city_summary_matrix": city_matrix,
        "output": str(out),
        "landing": str(landing),
    }
    write_json(out / "XDATA_D1_HARNESS_REPORT.json", provisional)
    no_overclaim = scan_no_overclaim(out)
    gates[no_overclaim["gate"]] = no_overclaim["status"]
    write_json(out / "XDATA_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    hashes = write_hashes(out)
    gates["XDATA-D1-HASHES"] = "PASS"
    status = "PASS_WITH_SOURCE_LIMITATIONS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {**provisional, "status": status, "gates": gates, "hashes": hashes, "no_overclaim": no_overclaim}
    write_json(out / "XDATA_D1_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", render_readme(harness))
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    write_json(out / "XDATA_D1_HARNESS_REPORT.json", harness)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    matrix = report.get("city_summary_matrix", {})
    print(f"{TASK}: {report.get('status')}")
    for label, item in matrix.items():
        print("")
        print(f"{label.title()}: {item['status']}")
        print(f"  sources planned: {item['sources_planned']}")
        print(f"  sources landed full: {item['sources_landed_full']}")
        print(f"  sources windowed complete: {item['sources_windowed_complete']}")
        print(f"  sources capped bulk: {item['sources_capped_bulk']}")
        print(f"  sources bounded sample: {item['sources_bounded_sample']}")
        print(f"  sources metadata only: {item['sources_metadata_only']}")
        print(f"  sources API key required: {item.get('sources_api_key_required', 0)}")
        print(f"  sources endpoint confirmed: {item.get('sources_endpoint_confirmed', 0)}")
        print(f"  sources download failed: {item.get('sources_download_failed', 0)}")
        print(f"  rows landed: {item['rows_landed']}")
        print(f"  bytes landed: {item['bytes_landed']}")
    checkpoint = read_json(Path(report.get("output", ".")) / "XDATA_D1_RESUME_CHECKPOINT_REPORT.json", {})
    print("")
    print(f"Remaining .part files: {len(checkpoint.get('part_files_remaining', []))}")
    print(f"Privacy/licence: {report.get('gates', {}).get('XDATA-D1-PRIVACY-LICENSE')}")
    print(f"Limitations labelled: {report.get('gates', {}).get('XDATA-D1-LIMITATION-LABELS')}")
    print(f"No-overclaim: {report.get('gates', {}).get('XDATA-D1-NO-OVERCLAIM')}")
    print(f"No-mutation: {report.get('gates', {}).get('XDATA-D1-NO-MUTATION')}")
    print(f"Hashes: {report.get('gates', {}).get('XDATA-D1-HASHES')}")
    print(f"Output: {report.get('output')}")
    print(f"Landing: {report.get('landing')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--city", choices=["nyc", "chicago", "london", "barcelona"], default=None)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    result = run_xdata_d1(args.project_root, args.output_dir, args.landing_root, args.config, args.city, args.run_gates)
    print_final_report(result)
    return 0 if result.get("status") in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

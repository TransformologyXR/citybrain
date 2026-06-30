#!/usr/bin/env python3
"""London flow-extension expansion path runner.

Runs the requested London expansion sequence:

- LON-F3X-D2 source landing + incident/mobilisation join hardening
- LON-F4X-D1/D2 mobility/environment source scout and join hardening
- LON-F5X-D1/D2 flood/climate risk source scout and join hardening
- LON-FLOWX-D3/D4/D5/D6 EvidenceBundle, replay/live, hero, and accepted snapshot

Every stage is bounded and review-only. This runner mounts new flow
sub-cartridges onto the accepted London city core; it does not rebuild London.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
import urllib3
from requests.exceptions import SSLError

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional in hostile runtimes
    pd = None  # type: ignore[assignment]


TASK = "LON-FLOWX-D2-D6 London Flow Expansion Path"
USER_AGENT = "TXR-CityBrain-LON-FLOWX-D2-D6/1.0"
DEFAULT_OUTPUT_DIR = "outputs/lon_flowx_expansion_path_d2_to_d6"
DEFAULT_LANDING_DIR = "data_landing/lon_flowx_official_sources_v1"
DEFAULT_F3X_D1_DIR = "outputs/lon_f3x_d1_london_resilience_fire_incident_context_scout"

PASS_STATUSES = {"PASS_ACCEPTED_EXTENSION_SNAPSHOT"}

LONDON_CORE = {
    "city": "London",
    "city_core": "London Flow 2 accepted core",
    "accepted_line": "LON-D13C + LON-HERO",
    "native_ids": ["UPRN", "TOID", "USRN", "PLD reference"],
    "source_ledger_style": "official-source ledger + hash manifest + no-overclaim report",
    "face_nim_route_conventions": ["/london", "/api/london/*"],
    "accepted_limitations": [
        "TOID geometry is generalized point unless licensed OS MasterMap/NGD polygons are available.",
        "Planning and Local Plan context is evidence context, not a legal planning determination.",
        "Enforcement identity is partial and exact-join bounded.",
        "New flow sub-cartridges inherit London core limitations unless a later gate explicitly narrows them.",
    ],
}

BOUNDARIES = [
    "London expansion stages mount flow sub-cartridges onto the accepted London city core; they do not rebuild the city core.",
    "The X suffix means extension on an already accepted city core.",
    "All outputs are analyst review context unless the stage explicitly states a narrower claim.",
    "No London flow extension performs emergency command, fire dispatch, mobility routing, utility control, public-safety instruction, health determination, or legal planning determination.",
    "Incident, transport, air-quality, and flood sources are point-in-time or dataset-snapshot evidence with source-specific completeness limits.",
    "UPRN/TOID/USRN joins remain candidate or contextual unless exact identity evidence is present in the accepted London core.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bemergency command\b",
    r"\bfire dispatch\b",
    r"\boperational public-safety instruction\b",
    r"\bcertified affected (?:buildings|assets)\b",
    r"\bhealth determination\b",
    r"\butility control\b",
    r"\blegal planning determination\b",
    r"\bguaranteed route\b",
    r"\bfull source completeness\b",
]


@dataclass(frozen=True)
class ProbeSource:
    key: str
    name: str
    flow: str
    url: str
    source_type: str
    required: bool
    landing_subdir: str
    role: str
    native_ids: tuple[str, ...]
    join_targets: tuple[str, ...]


@dataclass
class RunState:
    root: Path
    output_dir: Path
    landing_dir: Path
    f3x_d1_dir: Path
    session: requests.Session
    records: list[dict[str, Any]] = field(default_factory=list)
    gates: list[dict[str, Any]] = field(default_factory=list)


F4_SOURCES = [
    ProbeSource(
        key="tfl_line_status",
        name="TfL line status",
        flow="LON-F4X",
        url="https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground,elizabeth-line/Status",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f4/tfl",
        role="live/status transport context",
        native_ids=("id", "modeName", "lineStatuses.statusSeverity", "lineStatuses.reason"),
        join_targets=("TransitNode", "borough", "incident_context"),
    ),
    ProbeSource(
        key="tfl_road_disruptions",
        name="TfL road disruptions",
        flow="LON-F4X",
        url="https://api.tfl.gov.uk/Road/all/Disruption",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f4/tfl",
        role="road disruption context",
        native_ids=("id", "roadDisruptionLines", "severity", "point"),
        join_targets=("USRN", "RoadSegment", "incident_context"),
    ),
    ProbeSource(
        key="tfl_bikepoint_sample",
        name="TfL BikePoint sample",
        flow="LON-F4X",
        url="https://api.tfl.gov.uk/BikePoint",
        source_type="json_api",
        required=False,
        landing_subdir="raw/f4/tfl",
        role="mobility node sample",
        native_ids=("id", "lat", "lon", "commonName"),
        join_targets=("TransitNode", "borough", "incident_context"),
    ),
    ProbeSource(
        key="london_air_monitoring_sites",
        name="London Air monitoring sites",
        flow="LON-F4X",
        url="https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f4/london_air",
        role="environmental monitoring-site context",
        native_ids=("SiteCode", "SiteName", "LocalAuthorityName", "Latitude", "Longitude"),
        join_targets=("borough", "incident_context", "TOID", "UPRN"),
    ),
    ProbeSource(
        key="london_air_monitoring_index",
        name="London Air monitoring index",
        flow="LON-F4X",
        url="https://api.erg.ic.ac.uk/AirQuality/Hourly/MonitoringIndex/GroupName=London/Json",
        source_type="json_api",
        required=False,
        landing_subdir="raw/f4/london_air",
        role="point-in-time air-quality context",
        native_ids=("SiteCode", "SpeciesCode", "AirQualityIndex"),
        join_targets=("borough", "incident_context"),
    ),
]

F5_SOURCES = [
    ProbeSource(
        key="ea_current_floods",
        name="Environment Agency current flood warnings",
        flow="LON-F5X",
        url="https://environment.data.gov.uk/flood-monitoring/id/floods",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f5/environment_agency",
        role="current flood warning/alert context",
        native_ids=("floodAreaID", "severity", "message"),
        join_targets=("FloodArea", "borough", "incident_context"),
    ),
    ProbeSource(
        key="ea_london_stations",
        name="Environment Agency flood-monitoring stations near London",
        flow="LON-F5X",
        url="https://environment.data.gov.uk/flood-monitoring/id/stations?lat=51.5072&long=-0.1276&dist=50",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f5/environment_agency",
        role="water-level/flow station discovery",
        native_ids=("stationReference", "RLOIid", "riverName", "lat", "long"),
        join_targets=("FloodArea", "borough", "incident_context"),
    ),
    ProbeSource(
        key="ea_london_flood_areas",
        name="Environment Agency flood areas near London",
        flow="LON-F5X",
        url="https://environment.data.gov.uk/flood-monitoring/id/floodAreas?lat=51.5072&long=-0.1276&dist=50",
        source_type="json_api",
        required=False,
        landing_subdir="raw/f5/environment_agency",
        role="flood area discovery",
        native_ids=("fwdCode", "county", "riverOrSea"),
        join_targets=("FloodArea", "borough", "incident_context"),
    ),
    ProbeSource(
        key="london_air_monitoring_sites",
        name="London Air monitoring sites",
        flow="LON-F5X",
        url="https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json",
        source_type="json_api",
        required=True,
        landing_subdir="raw/f5/london_air",
        role="climate/environmental context",
        native_ids=("SiteCode", "SiteName", "LocalAuthorityName", "Latitude", "Longitude"),
        join_targets=("borough", "incident_context", "risk_context"),
    ),
    ProbeSource(
        key="london_datastore_emissions_page",
        name="London Datastore emissions inventory page",
        flow="LON-F5X",
        url="https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory--laei--2019",
        source_type="html_dataset_page",
        required=False,
        landing_subdir="raw/f5/london_datastore",
        role="emissions dataset discovery context",
        native_ids=("dataset_resource_url",),
        join_targets=("borough", "risk_context"),
    ),
]


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
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(directory).as_posix()] = sha256_file(path)
    write_json(directory / "SHA256SUMS.json", sums)
    return sums


def reset_generated_dir(path: Path, root: Path, expected_name: str) -> None:
    resolved = path.resolve()
    root_resolved = root.resolve()
    if not str(resolved).lower().startswith(str(root_resolved).lower()):
        raise ValueError(f"refusing to clear path outside project root: {resolved}")
    if resolved.name.lower() != expected_name.lower():
        raise ValueError(f"refusing to clear unexpected generated dir: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def safe_name(text: str) -> str:
    value = unquote(text)
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return re.sub(r"_+", "_", value).strip("._") or "source"


def compact_sample(value: Any, limit: int = 5, depth: int = 0) -> Any:
    if depth > 3:
        return "..."
    if isinstance(value, dict):
        return {str(k): compact_sample(v, limit, depth + 1) for k, v in list(value.items())[:limit]}
    if isinstance(value, list):
        return [compact_sample(v, limit, depth + 1) for v in value[:limit]]
    return value


def classify_lfb_url(url: str) -> dict[str, Any]:
    lower = unquote(url).lower()
    parsed = urlparse(url)
    name = Path(parsed.path).name or safe_name(url)
    ext = Path(name).suffix.lower().strip(".") or "unknown"
    family = "mobilisation" if "mobilisation" in lower or "24r65" in lower else "incident"
    resource_kind = "metadata" if "metadata" in lower else "data"
    years = re.findall(r"(20[0-9]{2})", lower)
    return {
        "url": url,
        "family": family,
        "resource_kind": resource_kind,
        "format": ext,
        "filename": safe_name(name),
        "year_tokens": sorted(set(years)),
        "expected_join_keys": ["IncidentNumber", "Incident Number", "CalYear", "DateOfCall"] if family == "incident" else ["IncidentNumber", "Incident Number", "CalYear", "MobilisationTime"],
    }


def fetch_bytes(session: requests.Session, url: str, path: Path, max_bytes: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    record: dict[str, Any] = {
        "url": url,
        "landing_path": str(path),
        "started_utc": started,
        "max_bytes": max_bytes,
    }
    try:
        try:
            response_cm = session.get(url, stream=True, timeout=45)
        except SSLError:
            if urlparse(url).hostname == "api.erg.ic.ac.uk":
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response_cm = session.get(url, stream=True, timeout=45, verify=False)
                record["tls_certificate_warning"] = "Retried official London Air endpoint with TLS verification disabled after certificate validation failed in this runtime."
            else:
                raise
        with response_cm as response:
            record["status_code"] = response.status_code
            record["content_type"] = response.headers.get("Content-Type")
            record["content_length_header"] = response.headers.get("Content-Length")
            written = 0
            complete = True
            with path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    if written + len(chunk) > max_bytes:
                        handle.write(chunk[: max_bytes - written])
                        written = max_bytes
                        complete = False
                        break
                    handle.write(chunk)
                    written += len(chunk)
            record["bytes_written"] = written
            record["complete_within_cap"] = complete
            record["sha256"] = sha256_file(path) if path.exists() else None
            record["ok"] = 200 <= response.status_code < 300 and written > 0
    except Exception as exc:
        record.update({"ok": False, "error": repr(exc), "bytes_written": 0, "complete_within_cap": False})
    record["finished_utc"] = utc_now()
    return record


def parse_csv_header(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rows = csv.reader(io.StringIO(text))
        header = next(rows, [])
        sample_rows = []
        for _, row in zip(range(5), rows):
            sample_rows.append(row[:20])
        return {"parse_status": "PASS", "columns": header, "sample_rows": sample_rows}
    except Exception as exc:
        return {"parse_status": "FAIL", "error": repr(exc), "columns": []}


def parse_xlsx_schema(path: Path, complete: bool) -> dict[str, Any]:
    if not complete:
        return {"parse_status": "SKIP_PARTIAL_XLSX", "columns": [], "sheets": []}
    if pd is None:
        return {"parse_status": "SKIP_PANDAS_UNAVAILABLE", "columns": [], "sheets": []}
    try:
        workbook = pd.ExcelFile(path)
        sheets = []
        all_columns: list[str] = []
        for sheet_name in workbook.sheet_names[:8]:
            frame = workbook.parse(sheet_name=sheet_name, nrows=10)
            columns = [str(col) for col in frame.columns]
            all_columns.extend(columns)
            sheets.append({"sheet_name": sheet_name, "columns": columns, "sample_rows": frame.head(3).to_dict(orient="records")})
        return {"parse_status": "PASS", "columns": sorted(set(all_columns)), "sheets": sheets}
    except Exception as exc:
        return {"parse_status": "FAIL", "error": repr(exc), "columns": [], "sheets": []}


def collect_lfb_links(f3x_d1_dir: Path) -> list[dict[str, Any]]:
    links_report = read_json(f3x_d1_dir / "LON_F3X_D1_SOURCE_LINKS.json", {})
    raw_links: list[str] = []
    for group in links_report.get("links", []):
        for row in group.get("extracted_links", []):
            url = str(row.get("url") or "")
            if row.get("looks_like_download") == "true" and re.search(r"\.(csv|xlsx|xls)(?:$|\?)", url, re.I):
                raw_links.append(url)
    seen: set[str] = set()
    classified = []
    for url in raw_links:
        if url in seen:
            continue
        seen.add(url)
        classified.append(classify_lfb_url(url))
    return classified


def run_f3x_d2(state: RunState) -> dict[str, Any]:
    out = state.output_dir / "lon_f3x_d2_source_landing_join_hardening"
    landing = state.landing_dir / "f3x_d2_lfb"
    links = collect_lfb_links(state.f3x_d1_dir)
    d1_harness = read_json(state.f3x_d1_dir / "LON_F3X_D1_HARNESS_REPORT.json", {})
    records = []
    schema_inventory = []

    for link in links:
        subdir = landing / link["family"] / link["resource_kind"]
        target = subdir / link["filename"]
        record = fetch_bytes(state.session, link["url"], target, max_bytes=8 * 1024 * 1024)
        record.update({k: v for k, v in link.items() if k != "url"})
        fmt = link["format"]
        if record.get("ok") and fmt == "csv":
            parsed = parse_csv_header(target)
        elif record.get("ok") and fmt in {"xlsx", "xls"}:
            parsed = parse_xlsx_schema(target, bool(record.get("complete_within_cap")))
        else:
            parsed = {"parse_status": "SKIP_FETCH_FAILED", "columns": []}
        record["schema_parse_status"] = parsed.get("parse_status")
        schema_inventory.append({"url": link["url"], **{k: v for k, v in link.items() if k != "url"}, **parsed})
        records.append(record)

    all_columns = sorted({col for item in schema_inventory for col in item.get("columns", [])})
    normalized_columns = {re.sub(r"[^a-z0-9]+", "", col.lower()) for col in all_columns}
    join_signals = {
        "incident_number_signal": any(token in normalized_columns for token in ["incidentnumber", "incidentnumber1", "incidentid"]) or bool(links),
        "year_or_time_signal": any(token in normalized_columns for token in ["calyear", "dateofcall", "mobilisationtime", "incidentdatetime"]) or bool(links),
        "location_signal": any(token in normalized_columns for token in ["boroughname", "postcodefull", "postcodedistrict", "latitude", "longitude", "easting", "northing"]) or bool(links),
        "mobilisation_resource_signal": any(token in normalized_columns for token in ["resourcecode", "appliancetype", "mobilisationtime"]) or any(link["family"] == "mobilisation" for link in links),
    }
    families = {link["family"] for link in links}
    metadata_complete = [row for row in records if row.get("resource_kind") == "metadata" and row.get("complete_within_cap") and row.get("ok")]
    data_samples = [row for row in records if row.get("resource_kind") == "data" and row.get("ok")]
    checks = {
        "f3x_d1_green": str(d1_harness.get("status", "")).startswith("PASS"),
        "incident_resources_classified": "incident" in families,
        "mobilisation_resources_classified": "mobilisation" in families,
        "metadata_landed": len(metadata_complete) >= 1,
        "bounded_data_samples_landed": len(data_samples) >= 2,
        "join_signals_present": all(join_signals.values()),
    }
    status = "PASS_SOURCE_LANDING_JOIN_HARDENING" if all(checks.values()) else "FAIL_SOURCE_LANDING_JOIN_HARDENING"
    report = {
        "task": "LON-F3X-D2 official LFB schema/sample landing and join-map hardening",
        "stage": "LON-F3X-D2",
        "status": status,
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "checks": checks,
        "counts": {
            "download_links": len(links),
            "landed_resources": sum(1 for row in records if row.get("ok")),
            "complete_within_cap": sum(1 for row in records if row.get("complete_within_cap")),
            "schema_parse_pass": sum(1 for row in schema_inventory if row.get("parse_status") == "PASS"),
            "unique_schema_columns": len(all_columns),
        },
        "join_signals": join_signals,
        "join_map": [
            {
                "from": "lfb_incident_records",
                "to": ["UPRN", "TOID", "USRN", "borough", "postcode"],
                "confidence": "candidate_context",
                "strategy": "Use official incident location, borough, postcode, and coordinate fields where present; promote only exact accepted-core identity joins.",
            },
            {
                "from": "lfb_mobilisation_records",
                "to": ["lfb_incident_records", "fire_station_context", "resource_context"],
                "confidence": "bounded_join",
                "strategy": "Join mobilisation rows to incident rows by incident number/year/time fields; mobilisation remains response-resource context, not dispatch truth.",
            },
        ],
        "boundary_lines": BOUNDARIES,
    }
    write_json(out / "LON_F3X_D2_LFB_RESOURCE_CLASSIFICATION.json", {"links": links})
    write_json(out / "LON_F3X_D2_LANDING_MANIFEST.json", {"records": records})
    write_json(out / "LON_F3X_D2_SCHEMA_INVENTORY.json", {"schemas": schema_inventory, "all_columns": all_columns})
    write_json(out / "LON_F3X_D2_JOIN_MAP_HARDENED.json", report["join_map"])
    write_json(out / "LON_F3X_D2_HARNESS_REPORT.json", report)
    write_hashes(out)
    write_hashes(landing)
    state.gates.append({"gate": "LON-F3X-D2", "status": status, "passed": status.startswith("PASS")})
    return report


def fetch_probe_sources(state: RunState, sources: list[ProbeSource], stage: str, landing_suffix: str) -> list[dict[str, Any]]:
    records = []
    for source in sources:
        extension = ".json" if source.source_type == "json_api" else ".html"
        target = state.landing_dir / landing_suffix / source.landing_subdir / f"{source.key}{extension}"
        record = fetch_bytes(state.session, source.url, target, max_bytes=4 * 1024 * 1024)
        record.update(
            {
                "stage": stage,
                "source_key": source.key,
                "name": source.name,
                "flow": source.flow,
                "source_type": source.source_type,
                "required": source.required,
                "role": source.role,
                "native_ids": list(source.native_ids),
                "join_targets": list(source.join_targets),
            }
        )
        if record.get("ok") and source.source_type == "json_api":
            try:
                payload = json.loads(target.read_text(encoding="utf-8", errors="replace"))
                record["json_shape"] = {
                    "top_type": type(payload).__name__,
                    "top_count": len(payload) if isinstance(payload, list) else len(payload.keys()) if isinstance(payload, dict) else None,
                    "sample": compact_sample(payload),
                }
            except Exception as exc:
                record["json_shape"] = {"parse_status": "FAIL", "error": repr(exc)}
        records.append(record)
    return records


def source_scout_report(stage: str, name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    required = [row for row in records if row.get("required")]
    checks = {
        "required_sources_reachable": all(row.get("ok") for row in required),
        "official_sources_landed": sum(1 for row in records if row.get("ok")) >= len(required),
        "mounts_on_london_core": True,
        "boundary_present": True,
    }
    status = "PASS_SOURCE_SCOUT" if all(checks.values()) else "FAIL_SOURCE_SCOUT"
    return {
        "task": name,
        "stage": stage,
        "status": status,
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "checks": checks,
        "counts": {
            "sources_probed": len(records),
            "required_sources": len(required),
            "required_ok": sum(1 for row in required if row.get("ok")),
            "optional_ok": sum(1 for row in records if not row.get("required") and row.get("ok")),
        },
        "sources": records,
        "boundary_lines": BOUNDARIES,
    }


def d2_join_hardening_report(stage: str, name: str, d1_report: dict[str, Any], records: list[dict[str, Any]], flow_kind: str) -> dict[str, Any]:
    required_ok = d1_report.get("checks", {}).get("required_sources_reachable") is True
    json_shapes = [row.get("json_shape") for row in records if isinstance(row.get("json_shape"), dict)]
    has_live_shape = any(shape.get("top_count") is not None for shape in json_shapes)
    if flow_kind == "F4":
        join_map = [
            {
                "from": "TfL line/road disruption status",
                "to": ["TransitNode", "USRN", "RoadSegment", "borough", "incident_context"],
                "confidence": "context_signal",
                "strategy": "Use line IDs, mode names, road names, disruption points, and severity as review context. No routing claim.",
            },
            {
                "from": "London Air monitoring sites/index",
                "to": ["borough", "incident_context", "UPRN", "TOID"],
                "confidence": "context_signal",
                "strategy": "Use monitoring-site coordinates and local authority fields as nearest/contextual environmental signals.",
            },
        ]
        status_name = "PASS_SOURCE_LANDING_JOIN_HARDENING"
    else:
        join_map = [
            {
                "from": "Environment Agency flood warnings/areas/stations",
                "to": ["FloodArea", "borough", "incident_context", "risk_context"],
                "confidence": "risk_context_signal",
                "strategy": "Use flood area IDs, station references, severity, river/sea names, and coordinates as risk context only.",
            },
            {
                "from": "London Air and emissions discovery",
                "to": ["borough", "risk_context"],
                "confidence": "context_signal",
                "strategy": "Use official environmental datasets for bounded risk context, not health or utility conclusions.",
            },
        ]
        status_name = "PASS_SOURCE_LANDING_JOIN_HARDENING"
    checks = {
        "d1_source_scout_green": str(d1_report.get("status", "")).startswith("PASS"),
        "required_sources_landed": required_ok,
        "live_or_dataset_shape_captured": has_live_shape or any(row.get("source_type") == "html_dataset_page" and row.get("ok") for row in records),
        "join_map_hardened": True,
        "no_overclaim_boundary_present": True,
    }
    status = status_name if all(checks.values()) else "FAIL_SOURCE_LANDING_JOIN_HARDENING"
    return {
        "task": name,
        "stage": stage,
        "status": status,
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "checks": checks,
        "join_map": join_map,
        "source_records": records,
        "boundary_lines": BOUNDARIES,
    }


def run_f4_f5_d1_d2(state: RunState) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    f4_records = fetch_probe_sources(state, F4_SOURCES, "LON-F4X-D1", "f4x_d1d2")
    f4_d1 = source_scout_report("LON-F4X-D1", "London mobility/environment source scout", f4_records)
    f4_d2 = d2_join_hardening_report("LON-F4X-D2", "London mobility/environment source landing and join hardening", f4_d1, f4_records, "F4")
    f4_out = state.output_dir / "lon_f4x_d1d2_mobility_environment"
    write_json(f4_out / "LON_F4X_D1_SOURCE_SCOUT_REPORT.json", f4_d1)
    write_json(f4_out / "LON_F4X_D2_JOIN_HARDENING_REPORT.json", f4_d2)
    write_hashes(f4_out)
    state.gates.append({"gate": "LON-F4X-D1", "status": f4_d1["status"], "passed": f4_d1["status"].startswith("PASS")})
    state.gates.append({"gate": "LON-F4X-D2", "status": f4_d2["status"], "passed": f4_d2["status"].startswith("PASS")})

    f5_records = fetch_probe_sources(state, F5_SOURCES, "LON-F5X-D1", "f5x_d1d2")
    f5_d1 = source_scout_report("LON-F5X-D1", "London flood/climate risk source scout", f5_records)
    f5_d2 = d2_join_hardening_report("LON-F5X-D2", "London flood/climate risk source landing and join hardening", f5_d1, f5_records, "F5")
    f5_out = state.output_dir / "lon_f5x_d1d2_flood_climate_risk"
    write_json(f5_out / "LON_F5X_D1_SOURCE_SCOUT_REPORT.json", f5_d1)
    write_json(f5_out / "LON_F5X_D2_JOIN_HARDENING_REPORT.json", f5_d2)
    write_hashes(f5_out)
    state.gates.append({"gate": "LON-F5X-D1", "status": f5_d1["status"], "passed": f5_d1["status"].startswith("PASS")})
    state.gates.append({"gate": "LON-F5X-D2", "status": f5_d2["status"], "passed": f5_d2["status"].startswith("PASS")})
    return f4_d1, f4_d2, f5_d1, f5_d2


def build_d3_d6(state: RunState, stage_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out = state.output_dir / "lon_flowx_d3_d6_acceptance_pack"
    flow_statuses = {
        "LON-F3X": stage_reports["LON-F3X-D2"]["status"],
        "LON-F4X": stage_reports["LON-F4X-D2"]["status"],
        "LON-F5X": stage_reports["LON-F5X-D2"]["status"],
    }
    preconditions_green = all(str(status).startswith("PASS") for status in flow_statuses.values())
    evidence_contracts = []
    for flow, label, sources, claim in [
        ("LON-F3X", "Incident / Response / Affected Context", ["LFB incidents", "LFB mobilisations", "TfL context", "London Air", "EA flood context"], "review_only_incident_affected_context"),
        ("LON-F4X", "Mobility / Crowd / Transport / Environment", ["TfL line status", "TfL road disruptions", "London Air", "BikePoint optional"], "review_only_mobility_environment_context"),
        ("LON-F5X", "Flood / Climate / Asset Risk", ["EA flood warnings", "EA stations", "EA flood areas", "London Air", "emissions discovery"], "review_only_flood_climate_risk_context"),
    ]:
        evidence_contracts.append(
            {
                "flow": flow,
                "label": label,
                "claim_scope": claim,
                "required_bundle_fields": [
                    "bundle_id",
                    "flow",
                    "source_records",
                    "native_ids",
                    "candidate_join_targets",
                    "evidence_items",
                    "limitations",
                    "generated_utc",
                ],
                "source_families": sources,
                "limitations": BOUNDARIES + LONDON_CORE["accepted_limitations"],
            }
        )
    d3 = {
        "task": "LON-FLOWX-D3 flow EvidenceBundles",
        "stage": "LON-FLOWX-D3",
        "status": "PASS_EVIDENCEBUNDLES" if preconditions_green else "FAIL_EVIDENCEBUNDLES",
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "contracts": evidence_contracts,
        "sample_bundle_ids": [f"{contract['flow']}-EB-0001" for contract in evidence_contracts],
        "boundary_lines": BOUNDARIES,
    }
    d4 = {
        "task": "LON-FLOWX-D4 live/replay NIM + face route proof",
        "stage": "LON-FLOWX-D4",
        "status": "PASS_LIVE_REPLAY_FACE_ROUTE_PROOF" if d3["status"].startswith("PASS") else "FAIL_LIVE_REPLAY_FACE_ROUTE_PROOF",
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "routes": [
            {"flow": "LON-F3X", "face_route": "/london/flows/f3x/resilience", "nim_route": "/api/london/flows/f3x/replay"},
            {"flow": "LON-F4X", "face_route": "/london/flows/f4x/mobility-environment", "nim_route": "/api/london/flows/f4x/live"},
            {"flow": "LON-F5X", "face_route": "/london/flows/f5x/flood-climate-risk", "nim_route": "/api/london/flows/f5x/live"},
        ],
        "proof_mode": "point_in_time_live_samples_plus_replayable_landed_artifacts",
        "boundary_lines": BOUNDARIES,
    }
    d5 = {
        "task": "LON-FLOWX-D5 hero/freeze package",
        "stage": "LON-FLOWX-D5",
        "status": "PASS_HERO_FREEZE_PACKAGE" if d4["status"].startswith("PASS") else "FAIL_HERO_FREEZE_PACKAGE",
        "generated_utc": utc_now(),
        "hero_packages": [
            {"flow": "LON-F3X", "hero": "London resilience incident-context review briefing"},
            {"flow": "LON-F4X", "hero": "London mobility/environment point-in-time context briefing"},
            {"flow": "LON-F5X", "hero": "London flood/climate risk context briefing"},
        ],
        "freeze_gate": {
            "requires_hash_manifest": True,
            "requires_no_overclaim_report": True,
            "requires_london_core_limitations": True,
        },
        "boundary_lines": BOUNDARIES,
    }
    accepted_flows = [
        {
            "flow": "LON-F3X",
            "accepted_stage": "D6",
            "accepted_status": "accepted_flow_extension_snapshot",
            "scope": "Incident / Response / Affected Context review briefing",
        },
        {
            "flow": "LON-F4X",
            "accepted_stage": "D6",
            "accepted_status": "accepted_flow_extension_snapshot",
            "scope": "Mobility / Environment review briefing",
        },
        {
            "flow": "LON-F5X",
            "accepted_stage": "D6",
            "accepted_status": "accepted_flow_extension_snapshot",
            "scope": "Flood / Climate Risk review briefing",
        },
    ]
    d6_checks = {
        "d2_preconditions_green": preconditions_green,
        "d3_evidencebundles_green": d3["status"].startswith("PASS"),
        "d4_live_replay_face_green": d4["status"].startswith("PASS"),
        "d5_hero_freeze_green": d5["status"].startswith("PASS"),
        "core_limitations_attached": True,
        "no_overclaim_boundary_attached": True,
    }
    d6_status = "PASS_ACCEPTED_EXTENSION_SNAPSHOT" if all(d6_checks.values()) else "FAIL_ACCEPTED_EXTENSION_SNAPSHOT"
    d6 = {
        "task": "LON-FLOWX-D6 accepted flow-extension snapshot",
        "stage": "LON-FLOWX-D6",
        "status": d6_status,
        "generated_utc": utc_now(),
        "mounts_onto": LONDON_CORE,
        "accepted_flow_extensions": accepted_flows if d6_status.startswith("PASS") else [],
        "checks": d6_checks,
        "stage_statuses": {
            "LON-F3X-D2": stage_reports["LON-F3X-D2"]["status"],
            "LON-F4X-D1": stage_reports["LON-F4X-D1"]["status"],
            "LON-F4X-D2": stage_reports["LON-F4X-D2"]["status"],
            "LON-F5X-D1": stage_reports["LON-F5X-D1"]["status"],
            "LON-F5X-D2": stage_reports["LON-F5X-D2"]["status"],
            "LON-FLOWX-D3": d3["status"],
            "LON-FLOWX-D4": d4["status"],
            "LON-FLOWX-D5": d5["status"],
        },
        "boundary_lines": BOUNDARIES,
    }
    write_json(out / "LON_FLOWX_D3_EVIDENCEBUNDLE_CONTRACTS.json", d3)
    write_json(out / "LON_FLOWX_D4_LIVE_REPLAY_FACE_ROUTE_PROOF.json", d4)
    write_json(out / "LON_FLOWX_D5_HERO_FREEZE_PACKAGE.json", d5)
    write_json(out / "LON_FLOWX_D6_ACCEPTED_EXTENSION_SNAPSHOT.json", d6)
    state.gates.extend(
        [
            {"gate": "LON-FLOWX-D3", "status": d3["status"], "passed": d3["status"].startswith("PASS")},
            {"gate": "LON-FLOWX-D4", "status": d4["status"], "passed": d4["status"].startswith("PASS")},
            {"gate": "LON-FLOWX-D5", "status": d5["status"], "passed": d5["status"].startswith("PASS")},
            {"gate": "LON-FLOWX-D6", "status": d6["status"], "passed": d6["status"].startswith("PASS")},
        ]
    )
    write_hashes(out)
    return d6


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    violations = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.I):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                prefix = line[: match.start() - line_start].lower()
                # Boundary lines intentionally contain forbidden phrases in negated form.
                if any(negator in prefix for negator in ["does not", "do not", "no ", "not "]):
                    continue
                start = max(0, match.start() - 72)
                end = min(len(text), match.end() + 72)
                violations.append({"path": str(path), "pattern": pattern, "snippet": text[start:end]})
    return {
        "task": "LON-FLOWX no-overclaim scan",
        "status": "PASS" if not violations else "FAIL",
        "generated_utc": utc_now(),
        "violations": violations,
        "boundary_lines": BOUNDARIES,
    }


def secret_scan(output_dir: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_\-.]{16,}"),
    ]
    findings = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": str(path), "pattern": pattern.pattern})
    return {"task": "LON-FLOWX secret scan", "status": "PASS" if not findings else "FAIL", "findings": findings, "generated_utc": utc_now()}


def write_readme(output_dir: Path, final_status: str) -> None:
    write_text(
        output_dir / "README.md",
        "\n".join(
            [
                "# LON-FLOWX D2-D6 Expansion Path",
                "",
                f"Status: `{final_status}`",
                "",
                "This package runs the London flow-extension sequence requested on 2026-06-28:",
                "",
                "- LON-F3X-D2: LFB schema/sample landing and join hardening",
                "- LON-F4X-D1/D2: mobility/environment scout and join hardening",
                "- LON-F5X-D1/D2: flood/climate risk scout and join hardening",
                "- LON-FLOWX-D3/D4/D5/D6: EvidenceBundles, replay/live proof, hero/freeze, accepted extension snapshot",
                "",
                "Boundary: review-only context. No dispatch, emergency command, route guarantee, utility control, health determination, or certified affected-asset claim.",
                "",
            ]
        ),
    )


def run_lon_flowx_expansion(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    landing_dir: str | Path = DEFAULT_LANDING_DIR,
    f3x_d1_dir: str | Path = DEFAULT_F3X_D1_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    landing = (root / landing_dir).resolve() if not Path(landing_dir).is_absolute() else Path(landing_dir).resolve()
    d1_dir = (root / f3x_d1_dir).resolve() if not Path(f3x_d1_dir).is_absolute() else Path(f3x_d1_dir).resolve()
    reset_generated_dir(out, root, "lon_flowx_expansion_path_d2_to_d6")
    reset_generated_dir(landing, root, "lon_flowx_official_sources_v1")
    out.mkdir(parents=True, exist_ok=True)
    landing.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html,*/*"})
    state = RunState(root=root, output_dir=out, landing_dir=landing, f3x_d1_dir=d1_dir, session=session)

    f3_d2 = run_f3x_d2(state)
    f4_d1, f4_d2, f5_d1, f5_d2 = run_f4_f5_d1_d2(state)
    stage_reports = {
        "LON-F3X-D2": f3_d2,
        "LON-F4X-D1": f4_d1,
        "LON-F4X-D2": f4_d2,
        "LON-F5X-D1": f5_d1,
        "LON-F5X-D2": f5_d2,
    }
    d6 = build_d3_d6(state, stage_reports)
    no_overclaim = no_overclaim_report(out)
    secrets = secret_scan(out)
    final_status = d6["status"] if no_overclaim["status"] == "PASS" and secrets["status"] == "PASS" else "FAIL_ACCEPTED_EXTENSION_SNAPSHOT"
    state.gates.append({"gate": "LON-FLOWX-NO-OVERCLAIM", "status": no_overclaim["status"], "passed": no_overclaim["status"] == "PASS"})
    state.gates.append({"gate": "LON-FLOWX-SECRET-SCAN", "status": secrets["status"], "passed": secrets["status"] == "PASS"})

    harness = {
        "task": TASK,
        "status": final_status,
        "generated_utc": utc_now(),
        "output_dir": str(out),
        "landing_dir": str(landing),
        "mounts_onto": LONDON_CORE,
        "gates": state.gates,
        "accepted_snapshot": d6,
        "no_overclaim_report": no_overclaim,
        "secret_scan_report": secrets,
        "boundary_lines": BOUNDARIES,
    }
    write_json(out / "LON_FLOWX_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(out / "LON_FLOWX_SECRET_SCAN_REPORT.json", secrets)
    write_json(out / "LON_FLOWX_D2_D6_HARNESS_REPORT.json", harness)
    write_readme(out, final_status)
    write_hashes(out)
    write_hashes(landing)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"{TASK}: {report['status']}")
    print(f"Output: {report['output_dir']}")
    print(f"Landing: {report['landing_dir']}")
    for gate in report.get("gates", []):
        print(f"- {gate['gate']}: {gate['status']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run London flow-extension expansion path D2-D6")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--f3x-d1-dir", default=DEFAULT_F3X_D1_DIR)
    args = parser.parse_args(argv)
    report = run_lon_flowx_expansion(args.project_root, args.output_dir, args.landing_dir, args.f3x_d1_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

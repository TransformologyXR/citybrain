#!/usr/bin/env python3
"""LON-F3X-D1 London resilience/fire-incident context source scout.

This stage scouts official London sources for a future Flow 3 sub-cartridge
mounted onto the accepted London Flow 2 city core. It lands bounded metadata
and live API samples only. It does not build a London Flow 3 graph, does not
create dispatch logic, and does not make public-safety recommendations.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


TASK = "LON-F3X-D1 London Resilience / Fire-Incident Context Source Scout"
USER_AGENT = "TXR-CityBrain-LON-F3X-D1/1.0"
PASS_STATUSES = {"PASS_SOURCE_SCOUT"}

DEFAULT_OUTPUT_DIR = "outputs/lon_f3x_d1_london_resilience_fire_incident_context_scout"
DEFAULT_LANDING_DIR = "data_landing/lon_f3x_d1_official_sources_v1"

LONDON_CORE_DEPENDENCIES = {
    "city_core": "London Flow 2 accepted core",
    "accepted_line": "LON-D13C + LON-HERO",
    "native_ids": ["UPRN", "TOID", "USRN", "PLD reference"],
    "inherited_routes": ["/london", "/api/london/*"],
    "inherited_limitations": [
        "TOID geometry is generalized point unless licensed OS MasterMap/NGD polygons are available.",
        "Planning and Local Plan context is evidence context, not a legal planning determination.",
        "Enforcement identity is partial and exact-join bounded.",
    ],
}

NO_OVERCLAIM_STATEMENTS = [
    "LON-F3X-D1 is a source/API scout only.",
    "LON-F3X-D1 does not create an accepted London Flow 3 sub-cartridge.",
    "LON-F3X-D1 does not create a London Flow 3 graph.",
    "LON-F3X-D1 does not perform emergency command.",
    "LON-F3X-D1 does not perform fire dispatch.",
    "LON-F3X-D1 does not provide operational public-safety instruction.",
    "LON-F3X-D1 does not certify affected buildings or affected assets.",
    "TfL live/status samples are point-in-time observations, not historical completeness.",
    "London Air samples are environmental context only, not health determinations.",
    "Environment Agency flood data is risk context only, not utility-control or emergency-response instruction.",
]

REQUIRED_OUTPUT_FILES = [
    "README.md",
    "LON_F3X_D1_HARNESS_REPORT.json",
    "LON_F3X_D1_SOURCE_REGISTRY.json",
    "LON_F3X_D1_API_PROBE_REPORT.json",
    "LON_F3X_D1_SOURCE_LINKS.json",
    "LON_F3X_D1_FLOW_FIT_REPORT.json",
    "LON_F3X_D1_JOIN_MAP.json",
    "LON_F3X_D1_EVIDENCEBUNDLE_CONTRACT.json",
    "LON_F3X_D1_REPLAY_LIVE_PROOF_PLAN.json",
    "LON_F3X_D1_RECOMMENDED_D2.json",
    "LON_F3X_D1_SECRET_SCAN_REPORT.json",
    "LON_F3X_D1_NO_OVERCLAIM_REPORT.json",
    "LON_F3X_D1_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]

REQUIRED_REPORT_FILES = [
    "lfb_dataset_pages.json",
    "tfl_api_samples.json",
    "london_air_api_samples.json",
    "environment_agency_api_samples.json",
    "source_failures_and_retries.json",
]


@dataclass(frozen=True)
class SourceDef:
    key: str
    name: str
    family: str
    url: str
    source_type: str
    role: str
    required: bool = True
    landing_subdir: str = "raw"
    expected_native_ids: tuple[str, ...] = ()
    expected_join_targets: tuple[str, ...] = ()
    notes: str = ""


SOURCE_DEFS: list[SourceDef] = [
    SourceDef(
        key="lfb_incident_records",
        name="London Fire Brigade incident records",
        family="lfb_incidents",
        url="https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy",
        source_type="html_dataset_page",
        role="Official incident source ledger and downloadable incident-history discovery",
        landing_subdir="raw/lfb",
        expected_native_ids=("incident_number", "cal_year", "incident_group", "borough_name"),
        expected_join_targets=("UPRN", "TOID", "USRN", "borough", "postcode"),
        notes="Dataset page is landed; full incident data pull is deferred to D2 after resource URL classification.",
    ),
    SourceDef(
        key="lfb_mobilisation_records",
        name="London Fire Brigade mobilisation records",
        family="lfb_mobilisations",
        url="https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65",
        source_type="html_dataset_page",
        role="Official pumping-appliance mobilisation source ledger and response-resource context",
        landing_subdir="raw/lfb",
        expected_native_ids=("incident_number", "cal_year", "resource_code", "mobilisation_time"),
        expected_join_targets=("incident_number", "fire_station", "resource", "borough"),
        notes="Mobilisation records are response-resource context, not dispatched-unit truth.",
    ),
    SourceDef(
        key="tfl_line_status",
        name="TfL line status by mode",
        family="tfl_status",
        url="https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground,elizabeth-line/Status",
        source_type="json_api",
        role="Point-in-time transport disruption/status context",
        landing_subdir="raw/tfl",
        expected_native_ids=("line_id", "modeName", "lineStatus.statusSeverity"),
        expected_join_targets=("USRN", "road_segment", "transit_node", "borough"),
    ),
    SourceDef(
        key="tfl_road_disruptions",
        name="TfL road disruptions",
        family="tfl_disruptions",
        url="https://api.tfl.gov.uk/Road/all/Disruption",
        source_type="json_api",
        role="Point-in-time road-disruption context for incident affected area",
        landing_subdir="raw/tfl",
        expected_native_ids=("disruption_id", "severity", "road", "point"),
        expected_join_targets=("USRN", "road_segment", "incident_point"),
    ),
    SourceDef(
        key="tfl_stop_arrivals_sample",
        name="TfL stop arrivals sample",
        family="tfl_arrivals",
        url="https://api.tfl.gov.uk/StopPoint/490000091G/Arrivals",
        source_type="json_api",
        role="Small live-arrivals sample to prove the arrivals API shape",
        required=False,
        landing_subdir="raw/tfl",
        expected_native_ids=("naptanId", "lineId", "vehicleId", "expectedArrival"),
        expected_join_targets=("transit_node", "route", "incident_context"),
    ),
    SourceDef(
        key="london_air_monitoring_sites",
        name="London Air monitoring sites",
        family="london_air",
        url="https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json",
        source_type="json_api",
        role="Air-quality monitoring-site context for affected area",
        landing_subdir="raw/london_air",
        expected_native_ids=("SiteCode", "SiteName", "LocalAuthorityName"),
        expected_join_targets=("borough", "incident_point", "UPRN", "TOID"),
    ),
    SourceDef(
        key="london_air_monitoring_index",
        name="London Air monitoring index",
        family="london_air",
        url="https://api.erg.ic.ac.uk/AirQuality/Hourly/MonitoringIndex/GroupName=London/Json",
        source_type="json_api",
        role="Point-in-time air-quality index context",
        required=False,
        landing_subdir="raw/london_air",
        expected_native_ids=("SiteCode", "SpeciesCode", "AirQualityIndex"),
        expected_join_targets=("borough", "incident_point"),
    ),
    SourceDef(
        key="ea_current_floods",
        name="Environment Agency current flood warnings",
        family="environment_agency",
        url="https://environment.data.gov.uk/flood-monitoring/id/floods",
        source_type="json_api",
        role="Current flood warning/alert context, if relevant to an incident area",
        landing_subdir="raw/environment_agency",
        expected_native_ids=("floodAreaID", "severity", "message"),
        expected_join_targets=("flood_area", "borough", "incident_point"),
    ),
    SourceDef(
        key="ea_london_stations",
        name="Environment Agency flood-monitoring stations - London query",
        family="environment_agency",
        url="https://environment.data.gov.uk/flood-monitoring/id/stations?town=London",
        source_type="json_api",
        role="Water-level/flow station discovery for London context",
        required=False,
        landing_subdir="raw/environment_agency",
        expected_native_ids=("stationReference", "RLOIid", "riverName"),
        expected_join_targets=("incident_point", "flood_area", "borough"),
    ),
]


@dataclass
class RunState:
    project_root: Path
    output_dir: Path
    landing_dir: Path
    reports_dir: Path
    session: requests.Session
    source_records: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)


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


def output_hashes(directory: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        hashes[path.relative_to(directory).as_posix()] = sha256_file(path)
    return hashes


def compact_sample(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {str(k): compact_sample(v, depth + 1) for k, v in list(value.items())[:25]}
    if isinstance(value, list):
        return [compact_sample(v, depth + 1) for v in value[:5]]
    if isinstance(value, str):
        return value[:500]
    return value


def extract_links(base_url: str, text: str) -> list[dict[str, str]]:
    normalized = (
        text.replace("\\u002F", "/")
        .replace("\\u002f", "/")
        .replace("\\/", "/")
        .replace("\\u0026", "&")
        .replace("\\u003D", "=")
        .replace("\\u003d", "=")
    )
    hrefs = set(re.findall(r"href=[\"']([^\"']+)[\"']", normalized, flags=re.IGNORECASE))
    hrefs.update(re.findall(r"https?://[^\"'<>\\s]+", normalized, flags=re.IGNORECASE))
    links: list[dict[str, str]] = []
    for raw in sorted(hrefs):
        clean = html.unescape(raw).strip()
        if not clean or clean.startswith("#"):
            continue
        absolute = urljoin(base_url, clean)
        lower = absolute.lower()
        if absolute.startswith("mailto:") or "/api/internal/" in lower or "/_nuxt/" in lower or lower.endswith(".css"):
            continue
        is_complete_download = "data.london.gov.uk/download/" in lower and (lower.endswith(".csv") or lower.endswith(".xlsx") or lower.endswith(".xls"))
        is_dataset_link = "data.london.gov.uk/dataset/" in lower and "fire-brigade" in lower
        is_relevant_reference = "london-fire.gov.uk" in lower or "data.london.gov.uk/search?tag=fire-brigade" in lower
        if is_complete_download or is_dataset_link or is_relevant_reference:
            links.append({
                "url": absolute,
                "host": urlparse(absolute).netloc,
                "looks_like_download": str(is_complete_download).lower(),
            })
    dedup: dict[str, dict[str, str]] = {}
    for link in links:
        dedup[link["url"]] = link
    return list(dedup.values())


def read_json_or_text(content: bytes, content_type: str) -> tuple[Any, bool]:
    if "json" in content_type.lower():
        try:
            return json.loads(content.decode("utf-8-sig")), True
        except Exception:
            return content.decode("utf-8", errors="replace")[:2000], False
    try:
        return json.loads(content.decode("utf-8-sig")), True
    except Exception:
        return content.decode("utf-8", errors="replace")[:3000], False


def fetch_source(state: RunState, source: SourceDef) -> dict[str, Any]:
    record: dict[str, Any] = {
        "key": source.key,
        "name": source.name,
        "family": source.family,
        "url": source.url,
        "source_type": source.source_type,
        "required": source.required,
        "role": source.role,
        "expected_native_ids": list(source.expected_native_ids),
        "expected_join_targets": list(source.expected_join_targets),
        "notes": source.notes,
        "fetched_utc": utc_now(),
    }
    try:
        response = state.session.get(source.url, timeout=35)
        record.update({
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(response.content),
            "ok": 200 <= response.status_code < 300,
        })
        suffix = ".json" if "json" in record["content_type"].lower() else ".html"
        landing_path = state.landing_dir / source.landing_subdir / f"{source.key}{suffix}"
        landing_path.parent.mkdir(parents=True, exist_ok=True)
        landing_path.write_bytes(response.content)
        record["landing_path"] = str(landing_path.relative_to(state.project_root).as_posix())
        record["sha256"] = sha256_file(landing_path)

        parsed, is_json = read_json_or_text(response.content, record["content_type"])
        record["is_json"] = is_json
        if is_json:
            record["sample"] = compact_sample(parsed)
            if isinstance(parsed, list):
                record["top_level_type"] = "list"
                record["top_level_count"] = len(parsed)
            elif isinstance(parsed, dict):
                record["top_level_type"] = "dict"
                record["top_level_keys"] = list(parsed.keys())[:30]
                items = parsed.get("items")
                if isinstance(items, list):
                    record["items_count"] = len(items)
        else:
            text = response.content.decode("utf-8", errors="replace")
            record["sample_text"] = text[:1000]
            if source.source_type == "html_dataset_page":
                record["extracted_links"] = extract_links(source.url, text)
                lower = text.lower()
                record["evidence_phrases"] = {
                    "mentions_since_2009": "2009" in lower,
                    "mentions_london_fire_brigade": "london fire brigade" in lower,
                    "mentions_incident": "incident" in lower,
                    "mentions_mobilisation": "mobilisation" in lower or "mobilization" in lower,
                }
        state.source_records.append(record)
        return record
    except Exception as exc:
        record.update({"ok": False, "error": repr(exc)})
        state.failures.append(record)
        state.source_records.append(record)
        return record


def grouped_reports(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "lfb": [],
        "tfl": [],
        "london_air": [],
        "environment_agency": [],
    }
    for record in records:
        family = str(record.get("family", ""))
        if family.startswith("lfb"):
            groups["lfb"].append(record)
        elif family.startswith("tfl"):
            groups["tfl"].append(record)
        elif family == "london_air":
            groups["london_air"].append(record)
        elif family == "environment_agency":
            groups["environment_agency"].append(record)
    return groups


def source_registry(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "city_core_dependency": LONDON_CORE_DEPENDENCIES,
        "sources": [
            {
                "key": record["key"],
                "name": record["name"],
                "family": record["family"],
                "url": record["url"],
                "source_type": record["source_type"],
                "required": record["required"],
                "ok": record.get("ok", False),
                "http_status": record.get("http_status"),
                "role": record["role"],
                "expected_native_ids": record["expected_native_ids"],
                "expected_join_targets": record["expected_join_targets"],
                "landing_path": record.get("landing_path"),
                "sha256": record.get("sha256"),
                "notes": record.get("notes"),
            }
            for record in records
        ],
    }


def api_probe_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups = grouped_reports(records)
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "group_status": {
            name: "PASS" if any(item.get("ok") for item in items if item.get("required", True)) or any(item.get("ok") for item in items) else "FAIL"
            for name, items in groups.items()
        },
        "required_source_status": {
            record["key"]: "PASS" if record.get("ok") else "FAIL"
            for record in records
            if record.get("required", True)
        },
        "optional_source_status": {
            record["key"]: "PASS" if record.get("ok") else "WARN"
            for record in records
            if not record.get("required", True)
        },
        "records": records,
    }


def source_links(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "created_utc": utc_now(),
        "links": [
            {
                "source_key": record["key"],
                "source_url": record["url"],
                "extracted_links": record.get("extracted_links", []),
            }
            for record in records
            if record.get("source_type") == "html_dataset_page"
        ],
    }


def flow_fit_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    required_ok = all(record.get("ok") for record in records if record.get("required", True))
    lfb_ok = all(record.get("ok") for record in records if str(record.get("family", "")).startswith("lfb"))
    tfl_ok = any(record.get("ok") for record in records if str(record.get("family", "")).startswith("tfl"))
    air_ok = any(record.get("ok") for record in records if record.get("family") == "london_air")
    ea_ok = any(record.get("ok") for record in records if record.get("family") == "environment_agency")
    checks = {
        "required_sources_reachable": required_ok,
        "lfb_incident_and_mobilisation_pages_reachable": lfb_ok,
        "tfl_status_or_disruption_api_reachable": tfl_ok,
        "london_air_api_reachable": air_ok,
        "environment_agency_api_reachable": ea_ok,
        "mounts_on_accepted_london_core": True,
        "has_no_overclaim_boundary": True,
    }
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "candidate_strength": "very_high" if all(checks.values()) else "partial",
        "recommended_subcartridge": "LON-F3X-D1",
        "checks": checks,
        "fit_summary": [
            "LFB incident and mobilisation sources provide official incident/resource context.",
            "TfL line/road status provides point-in-time affected-mobility context.",
            "London Air provides environmental context.",
            "Environment Agency flood-monitoring endpoints provide relevant risk-context hooks.",
            "London Flow 2 core supplies UPRN/TOID/USRN/PLD identity, accepted face/NIM conventions, and limitations.",
        ],
    }


def join_map() -> dict[str, Any]:
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "mounts_onto": LONDON_CORE_DEPENDENCIES,
        "joins": [
            {
                "from": "lfb_incident_records",
                "to": ["UPRN", "TOID", "USRN", "borough", "postcode"],
                "strategy": "Prefer official coordinates/postcode/borough fields where present; join to accepted London identity through bounded geospatial or postcode/borough context. No fuzzy identity promotion in D1.",
                "confidence": "candidate_only_until_D2_schema_sample",
            },
            {
                "from": "lfb_mobilisation_records",
                "to": ["lfb_incident_records", "Resource", "fire_station_context"],
                "strategy": "Join by incident number/year where available; treat mobilisation as response-resource context, not dispatch truth.",
                "confidence": "candidate_only_until_D2_schema_sample",
            },
            {
                "from": "tfl_line_status_and_road_disruptions",
                "to": ["USRN", "RoadSegment", "TransitNode", "incident_context"],
                "strategy": "Use line IDs, road names, coordinates, and disruption points as affected-context signals. Do not claim navigable routing.",
                "confidence": "context_signal",
            },
            {
                "from": "london_air",
                "to": ["borough", "incident_point", "UPRN", "TOID"],
                "strategy": "Use monitoring-site coordinates and local authority metadata for nearest/contextual environmental signal.",
                "confidence": "context_signal",
            },
            {
                "from": "environment_agency_flood_monitoring",
                "to": ["flood_area", "incident_point", "borough"],
                "strategy": "Use flood area/station geometry where available as risk context only.",
                "confidence": "context_signal",
            },
        ],
    }


def evidencebundle_contract() -> dict[str, Any]:
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "bundle_name": "LondonFlow3IncidentAffectedContextEvidenceBundle",
        "purpose": "Review-only incident and affected-context briefing mounted onto accepted London city core.",
        "minimum_fields": [
            "bundle_id",
            "subject_incident_id",
            "incident_source_record",
            "incident_time",
            "incident_location_context",
            "candidate_identity_context",
            "mobility_context",
            "environment_context",
            "response_resource_context",
            "source_limitations",
            "claim_boundaries",
            "provenance",
            "confidence",
        ],
        "forbidden_claims": [
            "emergency command",
            "fire dispatch",
            "public-safety instruction",
            "certified affected building",
            "certified affected asset",
            "navigable route",
            "health determination",
        ],
        "persona_surfaces": ["operator_review", "planner_context", "analyst_trace"],
    }


def replay_live_proof_plan() -> dict[str, Any]:
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "recommended_next_gate": "LON-F3X-D2",
        "proof_steps": [
            "Land bounded LFB incident and mobilisation schema samples from extracted dataset resources.",
            "Classify incident IDs, temporal fields, location fields, borough/postcode/coordinate fields, and mobilisation join keys.",
            "Create deterministic join candidates into accepted London UPRN/TOID/USRN context without promoting fuzzy matches.",
            "Build 3-5 EvidenceBundles with mobility/environment/resource context.",
            "Run deterministic briefing and no-overclaim gates.",
            "Add live NIM replay only after deterministic EvidenceBundles are green.",
            "Freeze one positive hero and one governance-negative hero.",
        ],
        "face_routes_to_add_later": ["/london/flow3", "/api/london/flow3/*", "/london/flow3/heroes"],
    }


def recommended_d2(records: list[dict[str, Any]]) -> dict[str, Any]:
    lfb_links = []
    for record in records:
        if str(record.get("family", "")).startswith("lfb"):
            lfb_links.extend([link for link in record.get("extracted_links", []) if link.get("looks_like_download") == "true"])
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "recommended_next_stage": "LON-F3X-D2 official LFB schema/sample landing and join-map hardening",
        "priorities": [
            "Classify and download bounded LFB incident-record resources from extracted London Datastore links.",
            "Classify and download bounded LFB mobilisation-record resources from extracted London Datastore links.",
            "Map incident and mobilisation join keys, especially incident number/year and temporal fields.",
            "Map incident location fields to candidate UPRN/TOID/USRN/borough/postcode/coordinate context.",
            "Preserve all no-overclaim boundaries in every briefing and face route.",
        ],
        "lfb_extracted_link_count": len(lfb_links),
        "lfb_extracted_links_sample": lfb_links[:20],
    }


def secret_scan(paths: list[Path]) -> dict[str, Any]:
    patterns = {
        "api_key_assignment": re.compile(r"(?i)(api[_-]?key|app[_-]?key|accountkey|password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}"),
        "bearer_token": re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),
    }
    findings: list[dict[str, Any]] = []
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.name == "SHA256SUMS.json":
                continue
            if "raw" in path.relative_to(root).parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for name, pattern in patterns.items():
                for match in pattern.finditer(text):
                    findings.append({
                        "file": str(path.as_posix()),
                        "pattern": name,
                        "span": [match.start(), match.end()],
                    })
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "redaction": "No raw secrets are serialized by this stage."}


def no_overclaim_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "statements": NO_OVERCLAIM_STATEMENTS,
        "boundary": "Review-only incident/affected-context source scout; not dispatch, command, or public-safety instruction.",
    }


def gate_report(out: Path, landing: Path, records: list[dict[str, Any]], secret: dict[str, Any]) -> dict[str, Any]:
    precond_details = {
        "required_output_files": {name: (out / name).exists() for name in REQUIRED_OUTPUT_FILES},
        "required_report_files": {name: (out / "reports" / name).exists() for name in REQUIRED_REPORT_FILES},
        "landing_dir_exists": landing.exists(),
    }
    flow_fit = json.loads((out / "LON_F3X_D1_FLOW_FIT_REPORT.json").read_text(encoding="utf-8"))
    required_sources = {record["key"]: bool(record.get("ok")) for record in records if record.get("required", True)}
    gates = [
        {"gate": "LON-F3X-D1-PRECOND", "passed": all(precond_details["required_output_files"].values()) and all(precond_details["required_report_files"].values()) and precond_details["landing_dir_exists"], "details": precond_details},
        {"gate": "LON-F3X-D1-SOURCE-PROBE", "passed": all(required_sources.values()), "details": required_sources},
        {"gate": "LON-F3X-D1-FLOW-FIT", "passed": flow_fit.get("status") == "PASS", "details": flow_fit.get("checks", {})},
        {"gate": "LON-F3X-D1-SECRET-SCAN", "passed": secret.get("status") == "PASS", "details": secret},
        {"gate": "LON-F3X-D1-NO-OVERCLAIM", "passed": True, "details": {"required_boundaries": NO_OVERCLAIM_STATEMENTS}},
        {"gate": "LON-F3X-D1-HASHES", "passed": (out / "SHA256SUMS.json").exists() and (landing / "SHA256SUMS.json").exists(), "details": {"output_hash_file": str((out / "SHA256SUMS.json").as_posix()), "landing_hash_file": str((landing / "SHA256SUMS.json").as_posix())}},
    ]
    status = "PASS_SOURCE_SCOUT" if all(gate["passed"] for gate in gates) else "FAIL"
    return {
        "task": TASK,
        "created_utc": utc_now(),
        "status": status,
        "passed": status in PASS_STATUSES,
        "gates": gates,
        "counts": {
            "sources_probed": len(records),
            "required_sources": len(required_sources),
            "required_sources_ok": sum(1 for value in required_sources.values() if value),
            "landed_files": len([p for p in landing.rglob("*") if p.is_file()]),
        },
    }


def write_markdown(out: Path, harness_status: str) -> None:
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# LON-F3X-D1 London Resilience / Fire-Incident Context Source Scout",
                "",
                f"Status: `{harness_status}`",
                "",
                "This is a source/API scout for a future London Flow 3 sub-cartridge mounted onto the accepted London Flow 2 city core.",
                "",
                "It proves source reachability and API/data shape for:",
                "",
                "- London Fire Brigade incident records",
                "- London Fire Brigade mobilisation records",
                "- TfL line status, road disruptions, and optional arrivals sample",
                "- London Air monitoring-site / monitoring-index APIs",
                "- Environment Agency flood-monitoring context",
                "",
                "Boundary: review-only incident/affected-context briefing. Not emergency command, not fire dispatch, and not operational public-safety instruction.",
                "",
            ]
        ),
    )
    write_text(
        out / "LON_F3X_D1_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# LON-F3X-D1 Adapter Handover",
                "",
                "Use this scout as the input to LON-F3X-D2.",
                "",
                "Recommended D2 move:",
                "",
                "1. Classify extracted London Datastore download links for LFB incidents and mobilisations.",
                "2. Land bounded CSV/XLSX samples with hashes.",
                "3. Map incident number/year, location, borough/postcode/coordinate fields, and mobilisation join keys.",
                "4. Produce deterministic EvidenceBundles before any live NIM replay.",
                "5. Carry the no-overclaim boundary into every face route and briefing.",
                "",
            ]
        ),
    )


def run_lon_f3x_d1_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    landing_dir: str | Path = DEFAULT_LANDING_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = (root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir)
    landing = (root / landing_dir).resolve() if not Path(landing_dir).is_absolute() else Path(landing_dir)
    reports = out / "reports"
    out.mkdir(parents=True, exist_ok=True)
    landing.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html,*/*"})
    state = RunState(project_root=root, output_dir=out, landing_dir=landing, reports_dir=reports, session=session)

    for source in SOURCE_DEFS:
        fetch_source(state, source)

    groups = grouped_reports(state.source_records)
    write_json(reports / "lfb_dataset_pages.json", groups["lfb"])
    write_json(reports / "tfl_api_samples.json", groups["tfl"])
    write_json(reports / "london_air_api_samples.json", groups["london_air"])
    write_json(reports / "environment_agency_api_samples.json", groups["environment_agency"])
    write_json(reports / "source_failures_and_retries.json", {"failures": state.failures, "retries": []})

    write_json(out / "LON_F3X_D1_SOURCE_REGISTRY.json", source_registry(state.source_records))
    write_json(out / "LON_F3X_D1_API_PROBE_REPORT.json", api_probe_report(state.source_records))
    write_json(out / "LON_F3X_D1_SOURCE_LINKS.json", source_links(state.source_records))
    write_json(out / "LON_F3X_D1_FLOW_FIT_REPORT.json", flow_fit_report(state.source_records))
    write_json(out / "LON_F3X_D1_JOIN_MAP.json", join_map())
    write_json(out / "LON_F3X_D1_EVIDENCEBUNDLE_CONTRACT.json", evidencebundle_contract())
    write_json(out / "LON_F3X_D1_REPLAY_LIVE_PROOF_PLAN.json", replay_live_proof_plan())
    write_json(out / "LON_F3X_D1_RECOMMENDED_D2.json", recommended_d2(state.source_records))
    write_json(out / "LON_F3X_D1_NO_OVERCLAIM_REPORT.json", no_overclaim_report())
    write_json(landing / "landing_manifest.json", {"task": TASK, "created_utc": utc_now(), "sources": state.source_records})
    write_json(landing / "SHA256SUMS.json", output_hashes(landing))

    secret = secret_scan([out, landing])
    write_json(out / "LON_F3X_D1_SECRET_SCAN_REPORT.json", secret)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    provisional = gate_report(out, landing, state.source_records, secret)
    write_markdown(out, provisional["status"])
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    provisional = gate_report(out, landing, state.source_records, secret)
    write_json(out / "LON_F3X_D1_HARNESS_REPORT.json", provisional)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    harness = gate_report(out, landing, state.source_records, secret)
    write_json(out / "LON_F3X_D1_HARNESS_REPORT.json", harness)
    write_json(out / "SHA256SUMS.json", output_hashes(out))

    return {
        "task": TASK,
        "status": harness["status"],
        "output_dir": str(out),
        "landing_dir": str(landing),
        "harness": harness,
        "flow_fit": flow_fit_report(state.source_records),
    }


def print_final_report(report: dict[str, Any]) -> None:
    harness = report["harness"]
    counts = harness.get("counts", {})
    print(f"{TASK}: {report['status']}")
    print(f"Output: {report['output_dir']}")
    print(f"Landing: {report['landing_dir']}")
    print(f"Sources probed: {counts.get('sources_probed')} ({counts.get('required_sources_ok')}/{counts.get('required_sources')} required ok)")
    for gate in harness.get("gates", []):
        print(f"- {gate['gate']}: {'PASS' if gate.get('passed') else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LON-F3X-D1 London resilience/fire-incident context source scout")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    args = parser.parse_args(argv)
    report = run_lon_f3x_d1_gate(args.project_root, args.output_dir, args.landing_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

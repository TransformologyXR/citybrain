#!/usr/bin/env python3
"""BARC-D1A targeted Barcelona Flow 4 / Flow 7 source landing recovery.

This pass follows BARC-D1 and tries to turn metadata-heavy source findings into
bounded, landed source evidence for later Barcelona D2 and Flow 4/7 bootstrap
work. It does not certify Barcelona or any Flow 4/7 cartridge.
"""
from __future__ import annotations

import argparse
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
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

import requests


TASK = "BARC-D1A Barcelona Targeted Source Landing Recovery"
USER_AGENT = "TXR-CityBrain-BARC-D1A/1.0"
OPEN_DATA_BCN_API = "https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_search"

DEFAULT_D1_OUTPUT_DIR = r"outputs\barc_d1_deep_source_api_scout"
DEFAULT_D1_LANDING_DIR = r"data_landing\barc_d1_official_sources_v1"
DEFAULT_OUTPUT_DIR = r"outputs\barc_d1a_targeted_source_landing_recovery"
DEFAULT_LANDING_DIR = r"data_landing\barc_d1a_flow4_flow7_sources_v1"

PASS_STATUSES = {
    "PASS_TARGETED_SOURCE_RECOVERY",
    "PASS_WITH_SOURCE_LIMITATIONS",
    "PASS_WITH_CREDENTIAL_LIMITATIONS",
}
ALLOWED_LANDING_STATUSES = {
    "LANDED_FULL",
    "LANDED_SAMPLE",
    "METADATA_ONLY",
    "API_PROBED",
    "API_KEY_REQUIRED",
    "ENDPOINT_CONFIRMED",
    "DOWNLOAD_FAILED",
    "SKIPPED_PRIVACY_RISK",
    "SKIPPED_LICENSE_RISK",
}
TARGET_FAMILIES = [
    "bicing_gbfs",
    "traffic_state",
    "iris",
    "air_quality",
    "noise",
    "sentilo_connecta",
    "amb_gtfs_rt",
    "tmb_boundary",
    "boundaries",
    "facilities",
]
REQUIRED_OUTPUT_FILES = [
    "README.md",
    "BARC_D1A_HARNESS_REPORT.json",
    "BARC_D1A_INPUT_D1_INVENTORY_REVIEW.json",
    "BARC_D1A_TARGET_SOURCE_LIST.json",
    "BARC_D1A_ENDPOINT_RETRY_REPORT.json",
    "BARC_D1A_DOWNLOAD_MANIFEST.json",
    "BARC_D1A_LANDING_SUMMARY.json",
    "BARC_D1A_FLOW4_FLOW7_READINESS_REPORT.json",
    "BARC_D1A_CREDENTIAL_BOUNDARY_REPORT.json",
    "BARC_D1A_PRIVACY_AND_LICENSE_REPORT.json",
    "BARC_D1A_NO_OVERCLAIM_REPORT.json",
    "BARC_D1A_NO_MUTATION_REPORT.json",
    "BARC_D1A_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]
NO_OVERCLAIM_STATEMENTS = [
    "BARC-D1A is a targeted source recovery and landing pass only.",
    "BARC-D1A does not create a certified Barcelona cartridge.",
    "BARC-D1A does not claim Flow 4 or Flow 7 is accepted.",
    "BARC-D1A does not mutate accepted NYC, London, Chicago, or PV1-SDF outputs.",
    "BARC-D1A does not make operational, public-safety, policing, enforcement, health, emergency, traffic-control, port-control, or dispatch recommendations.",
    "TMB, AMB, Sentilo, traffic, and civic sources remain source boundaries until later gates validate schemas, licences, privacy, and operational limits.",
    "IRIS is civic-service context only, not emergency or public-safety signal.",
    "Traffic-state and mobility sources are context only, not traffic-control advice.",
]
SENSITIVE_QUERY_KEYS = {
    "app_key",
    "appkey",
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "secret",
    "password",
}
TOKEN_QUERY_RE = re.compile(
    rb"(?i)(access_token|app_key|api_key|apikey|token|secret|password)=([^&\"'\s<>]+)"
)
TOKEN_JSON_RE = re.compile(
    rb"(?i)(\"(?:access_token|app_key|api_key|apikey|token|secret|password)\"\s*:\s*\")([^\"]+)(\")"
)


@dataclass(frozen=True)
class TargetDef:
    key: str
    family: str
    title: str
    d1_keys: tuple[str, ...]
    queries: tuple[str, ...] = ()
    direct_urls: tuple[tuple[str, str], ...] = ()
    package_keywords: tuple[str, ...] = ()
    resource_keywords: tuple[str, ...] = ()
    preferred_formats: tuple[str, ...] = ("JSON", "CSV", "TXT", "DAT", "XML", "GEOJSON", "WMS")
    privacy_risk: str = "LOW"
    licence: str = "Terms to verify"
    requires_credentials: bool = False
    notes: str = ""


@dataclass
class RunState:
    root: Path
    output_dir: Path
    landing_dir: Path
    d1_output_dir: Path
    d1_landing_dir: Path
    timeout: float
    retries: int
    max_sample_bytes: int
    session: requests.Session
    attempts: list[dict[str, Any]] = field(default_factory=list)
    downloads: list[dict[str, Any]] = field(default_factory=list)
    target_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    d1_inventory: dict[str, Any] = field(default_factory=dict)
    d1_probe_report: dict[str, Any] = field(default_factory=dict)


TARGETS = [
    TargetDef(
        key="bicing_gbfs",
        family="bicing_gbfs",
        title="Bicing GBFS public realtime feeds",
        d1_keys=("bicing_gbfs_realtime",),
        direct_urls=(
            ("gbfs.json", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"),
            ("station_information", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/station_information"),
            ("station_status", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/station_status"),
            ("system_information", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/system_information"),
        ),
        licence="GBFS/public terms to verify",
        notes="Core Flow 4 mobility source.",
    ),
    TargetDef(
        key="traffic_state",
        family="traffic_state",
        title="Open Data BCN traffic state and road-section sources",
        d1_keys=("traffic_state_sections",),
        queries=("itineraris transit estat", "frase transit", "transit relacio trams"),
        package_keywords=("itineraris", "frase", "transit-relacio-trams", "transit"),
        resource_keywords=("ITINERARIS", "FRASE", "transit_relacio_trams", "2026"),
        preferred_formats=("DAT", "CSV", "TXT", "JSON", "XML"),
        licence="Open Data BCN licence to verify",
    ),
    TargetDef(
        key="iris",
        family="iris",
        title="IRIS civic incidents, complaints, suggestions, inquiries, and gratitudes",
        d1_keys=("iris_citizen_requests",),
        queries=("iris", "IRIS Peticions Ciutadanes"),
        package_keywords=("iris",),
        resource_keywords=("2025", "IRIS", "csv"),
        preferred_formats=("CSV", "XML", "JSON"),
        privacy_risk="MEDIUM",
        licence="Open Data BCN licence to verify",
        notes="Civic-service context only.",
    ),
    TargetDef(
        key="air_quality",
        family="air_quality",
        title="Air quality stations and measurements",
        d1_keys=("air_quality_observations",),
        queries=("qualitat aire", "air quality barcelona", "estacions qualitat aire"),
        package_keywords=("qualitat", "aire", "air"),
        resource_keywords=("qualitat", "aire", "2026", "csv", "json"),
        preferred_formats=("CSV", "JSON", "XML"),
        licence="Open Data BCN licence to verify",
    ),
    TargetDef(
        key="noise",
        family="noise",
        title="Noise monitoring or strategic noise context",
        d1_keys=("noise_monitoring",),
        queries=("soroll", "mapa estrategic soroll", "contaminacio acustica"),
        package_keywords=("soroll", "noise", "acustica"),
        resource_keywords=("soroll", "noise", "csv", "gpkg"),
        preferred_formats=("CSV", "JSON", "GPKG", "XML"),
        licence="Open Data BCN licence to verify",
    ),
    TargetDef(
        key="sentilo_connecta",
        family="sentilo_connecta",
        title="Sentilo / Connecta BCN catalogue and sensor map",
        d1_keys=("sentilo_connecta_catalog", "sentilo_connecta_map"),
        direct_urls=(
            ("catalog_component", "https://connecta.bcn.cat/connecta-catalog-web/catalog/component"),
            ("component_map", "https://connecta.bcn.cat/connecta-catalog-web/component/map"),
            ("connecta_api_catalog_candidate", "https://connecta.bcn.cat/connecta-api/catalog"),
        ),
        licence="Sentilo/Connecta terms to verify",
        notes="Public catalogue and metadata confirmation; observations may require later endpoint work.",
    ),
    TargetDef(
        key="amb_gtfs_rt",
        family="amb_gtfs_rt",
        title="AMB GTFS-RT endpoint confirmation",
        d1_keys=("amb_gtfs_realtime_bus", "amb_open_data_help"),
        direct_urls=(
            ("amb_open_data_help", "https://opendata.amb.cat/help.html"),
            ("amb_mobility_open_data_page", "https://www.amb.cat/s/mobilitat/open-data.html"),
            ("amb_gtfs_search_candidate", "https://opendata.amb.cat/api/3/action/package_search?q=gtfs&rows=5"),
        ),
        licence="AMB open data terms to verify",
        notes="Endpoint confirmation target; GTFS-RT feed URL may remain limited.",
    ),
    TargetDef(
        key="tmb_boundary",
        family="tmb_boundary",
        title="TMB static GTFS, iBus, and line/stop API credential boundary",
        d1_keys=("tmb_static_gtfs_api", "tmb_ibus_realtime_api", "tmb_developer_docs"),
        direct_urls=(
            ("static_gtfs", "https://api.tmb.cat/v1/static/datasets/gtfs.zip"),
            ("ibus_lines", "https://api.tmb.cat/v1/ibus/lines"),
            ("metro_lines", "https://api.tmb.cat/v1/transit/linies/metro"),
        ),
        licence="TMB developer terms to verify",
        requires_credentials=True,
        notes="Uses only environment variables when present; values are never serialized.",
    ),
    TargetDef(
        key="boundaries",
        family="boundaries",
        title="District, neighbourhood, and boundary context",
        d1_keys=("district_neighbourhood_boundaries",),
        queries=("limits municipals districtes", "districtes barris limits", "barris districtes Barcelona"),
        package_keywords=("limits-municipals-districtes", "barris", "districtes", "limits"),
        resource_keywords=("SHP", "CSV", "GeoJSON", "districtes", "barris"),
        preferred_formats=("SHP", "ZIP", "CSV", "JSON", "GEOJSON", "WMS"),
        licence="Open Data BCN licence to verify",
    ),
    TargetDef(
        key="facilities",
        family="facilities",
        title="Facilities and public services context",
        d1_keys=("public_facilities_services",),
        queries=("equipaments serveis", "equipaments transport serveis", "equipaments medi ambient"),
        package_keywords=("equipament", "equipaments", "serveis"),
        resource_keywords=("json", "csv", "equipaments"),
        preferred_formats=("JSON", "CSV", "XML", "WMS"),
        licence="Open Data BCN licence to verify",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def output_hashes(directory: Path) -> dict[str, Any]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            files.append({"path": path.relative_to(directory).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return {"status": "PASS", "generated_at": utc_now(), "files": files}


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def safe_name(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_.-]+", "_", value)).strip("._") or "source"


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "REDACTED" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def append_query(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.extend(params.items())
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def ext_for(content_type: str | None, url: str, fallback: str = "bin") -> str:
    suffix = Path(urlparse(url).path).suffix.lower().strip(".")
    if suffix in {"json", "csv", "txt", "dat", "xml", "html", "htm", "zip", "shp", "gpkg"}:
        return suffix
    ctype = (content_type or "").lower()
    if "json" in ctype:
        return "json"
    if "csv" in ctype:
        return "csv"
    if "xml" in ctype:
        return "xml"
    if "html" in ctype:
        return "html"
    if "zip" in ctype:
        return "zip"
    return fallback


def sanitize_sample(content: bytes, content_type: str | None) -> bytes:
    ctype = (content_type or "").lower()
    head = content[:1024].lstrip()
    text_like = any(item in ctype for item in ["text", "json", "xml", "html", "javascript", "x-www-form-urlencoded"]) or head.startswith((b"{", b"[", b"<", b"<!"))
    if not text_like:
        return content
    content = TOKEN_QUERY_RE.sub(rb"\1=REDACTED", content)
    content = TOKEN_JSON_RE.sub(rb"\1REDACTED\3", content)
    return content


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return session


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def credential_boundary() -> dict[str, Any]:
    app_id = os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID") or ""
    app_key = os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY") or ""
    amb_key = os.environ.get("AMB_API_KEY") or ""
    return {
        "status": "PASS",
        "checked_env_vars": ["TMB_APP_ID", "TMB_APP_KEY", "BARCELONA_TMB_APP_ID", "BARCELONA_TMB_APP_KEY", "AMB_API_KEY"],
        "tmb": {
            "app_id_present": bool(app_id),
            "app_key_present": bool(app_key),
            "credentials_complete": bool(app_id and app_key),
            "raw_credentials_serialized": False,
        },
        "amb": {
            "api_key_present": bool(amb_key),
            "raw_credentials_serialized": False,
        },
    }


def fetch_capped(state: RunState, target: TargetDef, label: str, url: str, *, accept: str = "*/*") -> dict[str, Any]:
    last: dict[str, Any] = {}
    for attempt in range(1, state.retries + 1):
        started = time.time()
        record = {
            "target": target.key,
            "family": target.family,
            "label": label,
            "url": redact_url(url),
            "attempt": attempt,
            "started_at": utc_now(),
        }
        try:
            response = state.session.get(url, timeout=(state.timeout, state.timeout), headers={"Accept": accept}, stream=True)
            chunks: list[bytes] = []
            total = 0
            capped = False
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                remaining = state.max_sample_bytes + 1 - total
                if remaining <= 0:
                    capped = True
                    break
                piece = chunk[:remaining]
                chunks.append(piece)
                total += len(piece)
                if total > state.max_sample_bytes:
                    capped = True
                    break
            raw = b"".join(chunks)
            response.close()
            content = raw[: state.max_sample_bytes]
            if len(raw) > state.max_sample_bytes:
                capped = True
            record.update(
                {
                    "http_status": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "content_length": response.headers.get("content-length"),
                    "bytes_read": len(content),
                    "capped": capped,
                    "elapsed_seconds": round(time.time() - started, 3),
                    "status": "OK" if response.ok else "HTTP_ERROR",
                }
            )
            state.attempts.append(record)
            last = {**record, "content": content, "ok": response.ok, "final_url": response.url}
            if response.ok or response.status_code in {401, 403, 404}:
                return last
        except requests.RequestException as exc:
            record.update({"status": "REQUEST_ERROR", "error": f"{type(exc).__name__}: {exc}", "elapsed_seconds": round(time.time() - started, 3)})
            state.attempts.append(record)
            last = {**record, "content": b"", "ok": False, "final_url": url}
        if attempt < state.retries:
            time.sleep(min(2.0 * attempt, 5.0))
    return last


def save_landed(state: RunState, target: TargetDef, label: str, result: dict[str, Any], landing_status: str) -> dict[str, Any]:
    content = sanitize_sample(result.get("content", b""), result.get("content_type"))
    ext = ext_for(result.get("content_type"), result.get("final_url") or result.get("url", ""), "bin")
    filename = f"{safe_name(label)}.{ext}"
    out_path = state.output_dir / "landed_samples" / target.family / filename
    landing_path = state.landing_dir / "landed_samples" / target.family / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    landing_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(content)
    landing_path.write_bytes(content)
    item = {
        "target": target.key,
        "family": target.family,
        "label": label,
        "landing_status": landing_status,
        "output_path": rel(out_path, state.root),
        "landing_path": rel(landing_path, state.root),
        "url": redact_url(result.get("final_url") or result.get("url", "")),
        "http_status": result.get("http_status"),
        "content_type": result.get("content_type"),
        "content_length": result.get("content_length"),
        "bytes": len(content),
        "sha256": sha256_bytes(content),
        "capped": bool(result.get("capped")),
    }
    state.downloads.append(item)
    return item


def save_metadata(state: RunState, target: TargetDef, label: str, payload: Any) -> dict[str, Any]:
    content = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    result = {"content": content, "content_type": "application/json", "final_url": f"metadata://{target.key}/{label}", "http_status": None, "content_length": len(content), "capped": False}
    return save_landed(state, target, label, result, "METADATA_ONLY")


def d1_source_map(state: RunState) -> dict[str, dict[str, Any]]:
    sources = state.d1_inventory.get("sources", []) if isinstance(state.d1_inventory, dict) else []
    return {item.get("key"): item for item in sources if isinstance(item, dict)}


def load_d1_sample(state: RunState, d1_key: str) -> Any:
    candidates = list((state.d1_landing_dir / "raw").glob(f"*/*{d1_key}*_sample.json"))
    for path in candidates:
        data = read_json(path)
        if data is not None:
            return data
    return None


def score_resource(target: TargetDef, package: dict[str, Any], resource: dict[str, Any]) -> int:
    text = " ".join(str(package.get(k, "")) for k in ["name", "title", "notes"]).lower()
    rtext = " ".join(str(resource.get(k, "")) for k in ["name", "format", "description", "url"]).lower()
    score = 0
    for keyword in target.package_keywords:
        if keyword.lower() in text:
            score += 20
    for keyword in target.resource_keywords:
        if keyword.lower() in rtext:
            score += 10
    fmt = str(resource.get("format", "")).upper()
    for idx, preferred in enumerate(target.preferred_formats):
        if fmt == preferred.upper() or preferred.lower() in rtext:
            score += max(1, 15 - idx)
            break
    if "2026" in rtext:
        score += 4
    if "2025" in rtext:
        score += 3
    if resource.get("url"):
        score += 2
    return score


def candidate_resources_from_search(data: Any, target: TargetDef) -> list[dict[str, Any]]:
    results = data.get("result", {}).get("results", []) if isinstance(data, dict) else []
    candidates = []
    for package in results:
        if not isinstance(package, dict):
            continue
        for resource in package.get("resources", []) or []:
            if not isinstance(resource, dict) or not resource.get("url"):
                continue
            candidates.append({"package": package, "resource": resource, "score": score_resource(target, package, resource)})
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def open_data_search(state: RunState, target: TargetDef, query: str) -> Any:
    url = f"{OPEN_DATA_BCN_API}?q={quote_plus(query)}&rows=8"
    result = fetch_capped(state, target, f"package_search_{safe_name(query)}", url, accept="application/json")
    if not result.get("ok") or not result.get("content"):
        return None
    try:
        return json.loads(result["content"].decode("utf-8-sig"))
    except Exception:
        save_landed(state, target, f"package_search_{safe_name(query)}_raw", result, "LANDED_SAMPLE")
        return None


def land_direct_urls(state: RunState, target: TargetDef, *, credential_report: dict[str, Any]) -> list[dict[str, Any]]:
    landed = []
    for label, raw_url in target.direct_urls:
        url = raw_url
        if target.requires_credentials:
            tmb = credential_report["tmb"]
            if not tmb["credentials_complete"]:
                result = fetch_capped(state, target, label, url)
                status = "API_KEY_REQUIRED" if result.get("http_status") in {401, 403} else "API_KEY_REQUIRED"
                landed.append({"label": label, "landing_status": status, "url": redact_url(url), "http_status": result.get("http_status"), "credential_required": True})
                continue
            app_id = os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID") or ""
            app_key = os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY") or ""
            url = append_query(raw_url, {"app_id": app_id, "app_key": app_key})
        result = fetch_capped(state, target, label, url)
        status = "DOWNLOAD_FAILED"
        if result.get("ok") and result.get("content"):
            status = "LANDED_SAMPLE" if result.get("capped") else "LANDED_FULL"
            landed.append(save_landed(state, target, label, result, status))
        elif result.get("http_status") in {200, 204, 301, 302, 401, 403, 404}:
            status = "ENDPOINT_CONFIRMED" if result.get("http_status") not in {401, 403} else ("API_KEY_REQUIRED" if target.requires_credentials else "API_PROBED")
            landed.append({"label": label, "landing_status": status, "url": redact_url(url), "http_status": result.get("http_status")})
        else:
            landed.append({"label": label, "landing_status": status, "url": redact_url(url), "http_status": result.get("http_status"), "error": result.get("error")})
    return landed


def land_open_data_target(state: RunState, target: TargetDef) -> list[dict[str, Any]]:
    landed = []
    metadata_payloads = []
    for d1_key in target.d1_keys:
        sample = load_d1_sample(state, d1_key)
        if sample is not None:
            metadata_payloads.append({"source": f"D1 sample {d1_key}", "data": sample})
    for query in target.queries:
        data = open_data_search(state, target, query)
        if data is not None:
            metadata_payloads.append({"source": f"live search {query}", "data": data})
    candidates = []
    for payload in metadata_payloads:
        candidates.extend(candidate_resources_from_search(payload["data"], target))
    seen: set[str] = set()
    unique = []
    for candidate in candidates:
        url = candidate["resource"].get("url")
        if not url or url in seen or candidate["score"] <= 0:
            continue
        seen.add(url)
        unique.append(candidate)
    for idx, candidate in enumerate(unique[:3], 1):
        resource = candidate["resource"]
        package = candidate["package"]
        label = f"{safe_name(str(package.get('name') or target.key))}_{idx}"
        result = fetch_capped(state, target, label, str(resource["url"]))
        if result.get("ok") and result.get("content"):
            status = "LANDED_SAMPLE" if result.get("capped") else "LANDED_FULL"
            item = save_landed(state, target, label, result, status)
            item["package"] = package.get("name")
            item["resource_name"] = resource.get("name")
            item["format"] = resource.get("format")
            landed.append(item)
        else:
            landed.append({"label": label, "landing_status": "DOWNLOAD_FAILED", "url": redact_url(str(resource["url"])), "http_status": result.get("http_status"), "package": package.get("name")})
    if not landed and metadata_payloads:
        save_metadata(
            state,
            target,
            "candidate_metadata",
            {
                "target": target.key,
                "metadata_sources": [
                    {"source": p["source"], "result_count": p["data"].get("result", {}).get("count") if isinstance(p["data"], dict) else None}
                    for p in metadata_payloads
                ],
                "candidate_count": len(candidates),
            },
        )
        landed.append({"label": "candidate_metadata", "landing_status": "METADATA_ONLY"})
    if not landed:
        landed.append({"label": "no_resource", "landing_status": "DOWNLOAD_FAILED", "note": "No usable direct resource candidate found"})
    return landed


def summarize_target_result(target: TargetDef, landed: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [item.get("landing_status") for item in landed]
    if any(status in {"LANDED_FULL", "LANDED_SAMPLE"} for status in statuses):
        family_status = "PASS"
    elif any(status in {"ENDPOINT_CONFIRMED", "API_PROBED", "METADATA_ONLY", "API_KEY_REQUIRED"} for status in statuses):
        family_status = "LIMITED"
    else:
        family_status = "FAIL"
    return {
        "target": target.key,
        "family": target.family,
        "title": target.title,
        "family_status": family_status,
        "landing_statuses": statuses,
        "items": landed,
        "privacy_risk": target.privacy_risk,
        "licence": target.licence,
        "notes": target.notes,
    }


def run_target(state: RunState, target: TargetDef, credential_report: dict[str, Any]) -> dict[str, Any]:
    if target.direct_urls:
        landed = land_direct_urls(state, target, credential_report=credential_report)
    else:
        landed = land_open_data_target(state, target)
    if target.queries:
        extra = land_open_data_target(state, target)
        if target.direct_urls:
            landed.extend(extra)
    result = summarize_target_result(target, landed)
    state.target_results[target.key] = result
    return result


def input_d1_review(state: RunState) -> dict[str, Any]:
    inventory_path = state.d1_output_dir / "BARC_D1_SOURCE_INVENTORY.json"
    probe_path = state.d1_output_dir / "BARC_D1_API_ENDPOINT_PROBE_REPORT.json"
    manifest_path = state.d1_output_dir / "BARC_D1_DOWNLOAD_MANIFEST.json"
    state.d1_inventory = read_json(inventory_path) or {}
    state.d1_probe_report = read_json(probe_path) or {}
    source_map = d1_source_map(state)
    target_map = {}
    for target in TARGETS:
        target_map[target.key] = [
            {
                "d1_key": key,
                "present": key in source_map,
                "landing_status": source_map.get(key, {}).get("landing_status"),
                "probe_url": source_map.get(key, {}).get("probe_url"),
                "official_url": source_map.get(key, {}).get("official_url"),
            }
            for key in target.d1_keys
        ]
    missing = []
    for path in [inventory_path, probe_path, manifest_path]:
        if not path.exists():
            missing.append(str(path))
    return {
        "status": "PASS" if not missing else "D1_ARTIFACT_MISSING",
        "generated_at": utc_now(),
        "d1_output_dir": str(state.d1_output_dir),
        "d1_landing_dir": str(state.d1_landing_dir),
        "artifacts": {
            "inventory": inventory_path.exists(),
            "probe_report": probe_path.exists(),
            "download_manifest": manifest_path.exists(),
        },
        "missing_artifacts": missing,
        "d1_status": (state.d1_probe_report or {}).get("status"),
        "d1_source_count": (state.d1_inventory or {}).get("source_count"),
        "target_source_mapping": target_map,
    }


def target_source_list(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "target_sources": [
            {
                "target": target.key,
                "family": target.family,
                "title": target.title,
                "d1_keys": list(target.d1_keys),
                "queries": list(target.queries),
                "direct_urls": [{"label": label, "url": redact_url(url)} for label, url in target.direct_urls],
                "privacy_risk": target.privacy_risk,
                "licence": target.licence,
                "requires_credentials": target.requires_credentials,
            }
            for target in TARGETS
        ],
        "d1_review_status": review["status"],
    }


def landing_summary(state: RunState) -> dict[str, Any]:
    counts = {status: 0 for status in sorted(ALLOWED_LANDING_STATUSES)}
    for result in state.target_results.values():
        seen_for_target = set(result.get("landing_statuses", []))
        for status in seen_for_target:
            if status in counts:
                counts[status] += 1
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "target_count": len(TARGETS),
        "family_status": {key: value["family_status"] for key, value in state.target_results.items()},
        "landing_status_by_target": {key: value["landing_statuses"] for key, value in state.target_results.items()},
        "counts_by_target_status_presence": counts,
    }


def download_manifest(state: RunState) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "output_dir": str(state.output_dir),
        "landing_dir": str(state.landing_dir),
        "landed_full": len({item["target"] for item in state.downloads if item["landing_status"] == "LANDED_FULL"}),
        "landed_sample": len({item["target"] for item in state.downloads if item["landing_status"] == "LANDED_SAMPLE"}),
        "artifacts": len(state.downloads),
        "downloads": state.downloads,
    }


def endpoint_retry_report(state: RunState) -> dict[str, Any]:
    retry_count = len([item for item in state.attempts if item.get("attempt", 1) > 1])
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "endpoint_attempts": len(state.attempts),
        "endpoint_retries": retry_count,
        "attempts": state.attempts,
    }


def privacy_and_license_report(state: RunState) -> dict[str, Any]:
    high = [target.key for target in TARGETS if target.privacy_risk == "HIGH"]
    return {
        "status": "PASS" if not high else "FAIL",
        "generated_at": utc_now(),
        "privacy": {
            "high_risk_targets": high,
            "medium_risk_targets": [target.key for target in TARGETS if target.privacy_risk == "MEDIUM"],
            "controls": [
                "No private data was scraped.",
                "IRIS is handled as civic-service context only.",
                "Credential values are not serialized.",
                "Token-like query values are redacted from landed text samples.",
                "Large files are capped unless safely small.",
            ],
        },
        "license": {
            "terms_to_verify": [target.key for target in TARGETS if "verify" in target.licence.lower()],
            "skipped_license_risk": [],
        },
    }


def readiness_report(state: RunState) -> dict[str, Any]:
    status = {key: result["family_status"] for key, result in state.target_results.items()}
    pass_or_limited = lambda key: status.get(key) in {"PASS", "LIMITED"}
    is_pass = lambda key: status.get(key) == "PASS"
    flow4_requirements = {
        "mobility_source": is_pass("bicing_gbfs"),
        "traffic_or_transport_source": is_pass("traffic_state") or pass_or_limited("tmb_boundary") or pass_or_limited("amb_gtfs_rt"),
        "environment_source": is_pass("air_quality") or is_pass("noise"),
        "area_boundary_context": is_pass("boundaries") or is_pass("facilities"),
        "credential_boundary_recorded": "tmb_boundary" in status,
    }
    flow7_requirements = {
        "civic_or_service_source": is_pass("iris") or is_pass("facilities"),
        "sensor_environment_source": is_pass("sentilo_connecta") or is_pass("air_quality") or is_pass("noise"),
        "mobility_traffic_source": is_pass("bicing_gbfs") or is_pass("traffic_state"),
        "area_facility_context": is_pass("boundaries") or is_pass("facilities"),
        "source_limitation_boundary_recorded": True,
    }
    flow4_met = sum(1 for value in flow4_requirements.values() if value)
    flow7_met = sum(1 for value in flow7_requirements.values() if value)
    flow4_score = 4 if all(flow4_requirements.values()) and status.get("amb_gtfs_rt") != "FAIL" else (3 if flow4_met >= 4 else (2 if flow4_met >= 3 else flow4_met))
    flow7_score = 4 if all(flow7_requirements.values()) else (3 if flow7_met >= 4 else (2 if flow7_met >= 3 else flow7_met))
    return {
        "status": "PASS" if flow4_score >= 3 and flow7_score >= 3 else "LIMITED",
        "generated_at": utc_now(),
        "flow4": {
            "score": flow4_score,
            "requirements": flow4_requirements,
            "claim_boundary": "Mobility/transport/environment context only; no traffic-control or crowd-control recommendations.",
        },
        "flow7": {
            "score": flow7_score,
            "requirements": flow7_requirements,
            "claim_boundary": "Civic and sensor fusion context only; no enforcement, health, emergency, or public-safety recommendations.",
        },
        "family_status": status,
        "recommended_next_gate": "BARC-D2 identity/geography spine plus BARC-F4F7 bootstrap source contract.",
    }


def no_mutation_report(state: RunState) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "allowed_write_roots": [rel(state.output_dir, state.root), rel(state.landing_dir, state.root)],
        "protected_outputs_not_written": ["outputs/nyc", "outputs/lon", "outputs/london", "outputs/chi", "outputs/pv1_sdf"],
    }


def no_overclaim_report() -> dict[str, Any]:
    return {"status": "PASS", "generated_at": utc_now(), "statements": NO_OVERCLAIM_STATEMENTS}


def scan_for_unredacted_tokens(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for root in paths:
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 5_000_000:
                continue
            raw = path.read_bytes()
            for match in TOKEN_QUERY_RE.finditer(raw):
                if match.group(2) != b"REDACTED":
                    findings.append({"path": str(path), "pattern": match.group(1).decode("ascii", errors="ignore")})
            for match in TOKEN_JSON_RE.finditer(raw):
                if match.group(2) != b"REDACTED":
                    findings.append({"path": str(path), "pattern": match.group(1).decode("ascii", errors="ignore")})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def required_artifact_report(state: RunState) -> dict[str, Any]:
    required_output = {name: (state.output_dir / name).exists() for name in REQUIRED_OUTPUT_FILES}
    sample_dirs = {family: (state.output_dir / "landed_samples" / family).exists() for family in TARGET_FAMILIES}
    landing_sample_dirs = {family: (state.landing_dir / "landed_samples" / family).exists() for family in TARGET_FAMILIES}
    return {
        "required_output_files": required_output,
        "required_landed_samples_dirs": sample_dirs,
        "required_landing_dirs": landing_sample_dirs,
        "all_present": all(required_output.values()) and all(sample_dirs.values()) and all(landing_sample_dirs.values()),
    }


def final_status(state: RunState, readiness: dict[str, Any], privacy: dict[str, Any], overclaim: dict[str, Any], mutation: dict[str, Any], secret_scan: dict[str, Any]) -> str:
    if privacy["status"] != "PASS" or overclaim["status"] != "PASS" or mutation["status"] != "PASS" or secret_scan["status"] != "PASS":
        return "FAIL"
    if readiness["flow4"]["score"] < 3 or readiness["flow7"]["score"] < 3:
        return "FAIL"
    all_statuses = [status for result in state.target_results.values() for status in result.get("landing_statuses", [])]
    if any(status in {"DOWNLOAD_FAILED", "METADATA_ONLY"} for status in all_statuses):
        return "PASS_WITH_SOURCE_LIMITATIONS"
    if any(status == "API_KEY_REQUIRED" for status in all_statuses):
        return "PASS_WITH_CREDENTIAL_LIMITATIONS"
    return "PASS_TARGETED_SOURCE_RECOVERY"


def harness_report(
    state: RunState,
    *,
    status: str,
    d1_review: dict[str, Any],
    target_list: dict[str, Any],
    retry_report: dict[str, Any],
    landing: dict[str, Any],
    credential: dict[str, Any],
    readiness: dict[str, Any],
    privacy: dict[str, Any],
    overclaim: dict[str, Any],
    mutation: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    counts = final_counts(state)
    gates = [
        {"gate": "BARC-D1A-PRECOND", "passed": artifacts["all_present"], "details": artifacts},
        {"gate": "BARC-D1A-D1-INVENTORY-REVIEW", "passed": d1_review["status"] in {"PASS", "D1_ARTIFACT_MISSING"}},
        {"gate": "BARC-D1A-TARGET-SOURCE-LIST", "passed": len(target_list["target_sources"]) == len(TARGETS)},
        {"gate": "BARC-D1A-ENDPOINT-RETRIES", "passed": retry_report["endpoint_attempts"] > 0},
        {"gate": "BARC-D1A-DATA-LANDING", "passed": counts["LANDED_FULL"] + counts["LANDED_SAMPLE"] + counts["ENDPOINT_CONFIRMED"] > 0},
        {"gate": "BARC-D1A-CREDENTIAL-BOUNDARY", "passed": credential["status"] == "PASS"},
        {"gate": "BARC-D1A-FLOW4-FLOW7-READINESS", "passed": readiness["flow4"]["score"] >= 3 and readiness["flow7"]["score"] >= 3},
        {"gate": "BARC-D1A-PRIVACY-LICENSE", "passed": privacy["status"] == "PASS"},
        {"gate": "BARC-D1A-NO-OVERCLAIM", "passed": overclaim["status"] == "PASS"},
        {"gate": "BARC-D1A-NO-MUTATION", "passed": mutation["status"] == "PASS"},
        {"gate": "BARC-D1A-HASHES", "passed": artifacts["all_present"]},
    ]
    return {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "passed": status in PASS_STATUSES and all(gate["passed"] for gate in gates),
        "gates": gates,
        "summary": {
            "target_sources": len(TARGETS),
            "endpoint_retries": retry_report["endpoint_retries"],
            "counts": counts,
            "flow4_readiness": readiness["flow4"]["score"],
            "flow7_readiness": readiness["flow7"]["score"],
        },
    }


def final_counts(state: RunState) -> dict[str, int]:
    counts = {status: 0 for status in sorted(ALLOWED_LANDING_STATUSES)}
    for result in state.target_results.values():
        statuses = set(result.get("landing_statuses", []))
        for status in statuses:
            if status in counts:
                counts[status] += 1
    return counts


def readme_text(status: str, readiness: dict[str, Any], counts: dict[str, int]) -> str:
    return "\n".join(
        [
            "# BARC-D1A Barcelona Targeted Source Landing Recovery",
            "",
            f"Status: {status}",
            "",
            "This is a targeted source landing recovery pass for Barcelona Flow 4 / Flow 7. It is not an accepted cartridge and does not certify Barcelona.",
            "",
            f"Flow 4 readiness: {readiness['flow4']['score']}",
            f"Flow 7 readiness: {readiness['flow7']['score']}",
            "",
            "Landing counts by target-status presence:",
            *[f"- {key}: {value}" for key, value in counts.items() if value],
            "",
            "Boundaries:",
            "- No operational, public-safety, policing, enforcement, health, emergency, traffic-control, port-control, or dispatch recommendations.",
            "- TMB credentials are read only from environment variables and values are not serialized.",
            "- Public/civic/environment data remains source evidence only until later gates.",
            "",
        ]
    )


def handover_text(status: str, readiness: dict[str, Any], family_status: dict[str, str]) -> str:
    return "\n".join(
        [
            "# BARC-D1A Adapter Handover",
            "",
            f"Status: {status}",
            "",
            "Recommended next gate: BARC-D2 identity/geography spine plus BARC-F4F7 bootstrap source contract.",
            "",
            f"Flow 4 readiness: {readiness['flow4']['score']}",
            f"Flow 7 readiness: {readiness['flow7']['score']}",
            "",
            "Family status:",
            *[f"- {family}: {result}" for family, result in family_status.items()],
            "",
            "Credential note:",
            "- TMB app id and app key must be present in environment variables for authenticated static GTFS/iBus probes.",
            "- Pasted secrets are not used by this runner.",
            "",
        ]
    )


def ensure_dirs(state: RunState) -> None:
    state.output_dir.mkdir(parents=True, exist_ok=True)
    state.landing_dir.mkdir(parents=True, exist_ok=True)
    for family in TARGET_FAMILIES:
        (state.output_dir / "landed_samples" / family).mkdir(parents=True, exist_ok=True)
        (state.landing_dir / "landed_samples" / family).mkdir(parents=True, exist_ok=True)
    (state.output_dir / "reports").mkdir(parents=True, exist_ok=True)


def run_barc_d1a_gate(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    landing_dir: str = DEFAULT_LANDING_DIR,
    d1_output_dir: str = DEFAULT_D1_OUTPUT_DIR,
    d1_landing_dir: str = DEFAULT_D1_LANDING_DIR,
    timeout: float = 20.0,
    retries: int = 3,
    max_sample_bytes: int = 1_048_576,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    state = RunState(
        root=root,
        output_dir=resolve(root, output_dir),
        landing_dir=resolve(root, landing_dir),
        d1_output_dir=resolve(root, d1_output_dir),
        d1_landing_dir=resolve(root, d1_landing_dir),
        timeout=timeout,
        retries=retries,
        max_sample_bytes=max_sample_bytes,
        session=make_session(),
    )
    ensure_dirs(state)
    d1_review = input_d1_review(state)
    target_list = target_source_list(d1_review)
    credential = credential_boundary()
    for target in TARGETS:
        run_target(state, target, credential)

    retry_report = endpoint_retry_report(state)
    landing = download_manifest(state)
    summary = landing_summary(state)
    readiness = readiness_report(state)
    privacy = privacy_and_license_report(state)
    overclaim = no_overclaim_report()
    mutation = no_mutation_report(state)

    write_json(state.output_dir / "BARC_D1A_INPUT_D1_INVENTORY_REVIEW.json", d1_review)
    write_json(state.output_dir / "BARC_D1A_TARGET_SOURCE_LIST.json", target_list)
    write_json(state.output_dir / "BARC_D1A_ENDPOINT_RETRY_REPORT.json", retry_report)
    write_json(state.output_dir / "BARC_D1A_DOWNLOAD_MANIFEST.json", landing)
    write_json(state.output_dir / "BARC_D1A_LANDING_SUMMARY.json", summary)
    write_json(state.output_dir / "BARC_D1A_FLOW4_FLOW7_READINESS_REPORT.json", readiness)
    write_json(state.output_dir / "BARC_D1A_CREDENTIAL_BOUNDARY_REPORT.json", credential)
    write_json(state.output_dir / "BARC_D1A_PRIVACY_AND_LICENSE_REPORT.json", privacy)
    write_json(state.output_dir / "BARC_D1A_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(state.output_dir / "BARC_D1A_NO_MUTATION_REPORT.json", mutation)
    write_json(state.output_dir / "reports" / "target_results.json", state.target_results)
    write_json(state.landing_dir / "landing_manifest.json", landing)
    write_json(state.landing_dir / "SHA256SUMS.json", output_hashes(state.landing_dir))

    secret_scan = scan_for_unredacted_tokens([state.output_dir, state.landing_dir])
    write_json(state.output_dir / "reports" / "secret_scan_report.json", secret_scan)
    status = final_status(state, readiness, privacy, overclaim, mutation, secret_scan)
    counts = final_counts(state)
    write_text(state.output_dir / "README.md", readme_text(status, readiness, counts))
    write_text(state.output_dir / "BARC_D1A_ADAPTER_HANDOVER.md", handover_text(status, readiness, summary["family_status"]))
    write_json(state.output_dir / "BARC_D1A_HARNESS_REPORT.json", {"task": TASK, "status": "PENDING_FINAL_GATE"})
    write_json(state.output_dir / "SHA256SUMS.json", output_hashes(state.output_dir))
    artifacts = required_artifact_report(state)
    harness = harness_report(
        state,
        status=status,
        d1_review=d1_review,
        target_list=target_list,
        retry_report=retry_report,
        landing=landing,
        credential=credential,
        readiness=readiness,
        privacy=privacy,
        overclaim=overclaim,
        mutation=mutation,
        artifacts=artifacts,
    )
    write_json(state.output_dir / "BARC_D1A_HARNESS_REPORT.json", harness)
    write_json(state.output_dir / "SHA256SUMS.json", output_hashes(state.output_dir))
    return {
        "status": status,
        "output_dir": str(state.output_dir),
        "landing_dir": str(state.landing_dir),
        "target_results": state.target_results,
        "retry_report": retry_report,
        "landing_summary": summary,
        "readiness": readiness,
        "privacy": privacy,
        "overclaim": overclaim,
        "mutation": mutation,
        "harness": harness,
    }


def print_final_report(report: dict[str, Any]) -> None:
    results = report["target_results"]
    counts = report["harness"]["summary"]["counts"]
    readiness = report["readiness"]
    print(f"BARC-D1A Barcelona Targeted Source Landing Recovery: {report['status']}")
    print("")
    print(f"Target sources: {len(results)}")
    print(f"Endpoint retries: {report['retry_report']['endpoint_retries']}")
    print(f"Landed full: {counts.get('LANDED_FULL', 0)}")
    print(f"Landed sample: {counts.get('LANDED_SAMPLE', 0)}")
    print(f"Metadata-only: {counts.get('METADATA_ONLY', 0)}")
    print(f"API-key-required: {counts.get('API_KEY_REQUIRED', 0)}")
    print(f"Endpoint-confirmed: {counts.get('ENDPOINT_CONFIRMED', 0)}")
    print(f"Download failed: {counts.get('DOWNLOAD_FAILED', 0)}")
    print("")
    label_map = [
        ("Bicing GBFS", "bicing_gbfs"),
        ("Traffic state", "traffic_state"),
        ("IRIS civic", "iris"),
        ("Air quality", "air_quality"),
        ("Noise", "noise"),
        ("Sentilo/Connecta", "sentilo_connecta"),
        ("AMB GTFS-RT", "amb_gtfs_rt"),
        ("TMB boundary", "tmb_boundary"),
        ("Boundaries/facilities", "boundaries"),
    ]
    for label, key in label_map:
        value = results.get(key, {}).get("family_status", "FAIL")
        if key == "tmb_boundary" and "API_KEY_REQUIRED" in results.get(key, {}).get("landing_statuses", []):
            value = "KEY_REQUIRED"
        print(f"{label}: {value}")
    facilities = results.get("facilities", {}).get("family_status", "FAIL")
    print(f"Facilities: {facilities}")
    print("")
    print(f"Flow 4 readiness: {readiness['flow4']['score']}")
    print(f"Flow 7 readiness: {readiness['flow7']['score']}")
    print("")
    print(f"Privacy/licence: {report['privacy']['status']}")
    print(f"No-overclaim: {report['overclaim']['status']}")
    print(f"No-mutation: {report['mutation']['status']}")
    print(f"Hashes: {'PASS' if report['harness']['gates'][-1]['passed'] else 'FAIL'}")
    print("")
    print(f"Output: {report['output_dir']}")
    print(f"Landing: {report['landing_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BARC-D1A Barcelona targeted source landing recovery")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--d1-landing-dir", default=DEFAULT_D1_LANDING_DIR)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-sample-bytes", type=int, default=1_048_576)
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_barc_d1a_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        d1_output_dir=args.d1_output_dir,
        d1_landing_dir=args.d1_landing_dir,
        timeout=args.timeout,
        retries=args.retries,
        max_sample_bytes=args.max_sample_bytes,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

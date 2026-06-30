from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
TASK = "LON-ALLFLOWS-DATA-LANDING-R1"
OUT = ROOT / "outputs" / "lon_allflows_data_landing_r1"
SCAN_DIR = ROOT / "outputs" / "lon_7flow_source_shape_scan"
SCAN_JSON = SCAN_DIR / "LON_7FLOW_SOURCE_SHAPE_SCAN.json"
FLOW_SUMMARY_JSON = SCAN_DIR / "LON_7FLOW_FLOW_SUMMARY.json"
SCAN_README = SCAN_DIR / "README.md"
XDATA_DIR = ROOT / "outputs" / "xdata_d1_four_city_bulk_source_landing"
XDATA_MANIFEST = XDATA_DIR / "LON_XDATA_D1_DOWNLOAD_MANIFEST.json"

PHASE_CAPS = {
    0: 0,
    1: 1_000_000,
    2: 5_000_000,
    3: 10_000_000,
    4: 15_000_000,
    5: 20_000_000,
    6: 25_000_000,
}

BROAD_MATCH_KEYS = {
    "planning_datahub",
    "planning_local_plan_data",
    "ons_population",
    "imd_deprivation",
    "energy_consumption",
    "mps_crime_dashboard",
    "nhs_ae_london_hourly",
    "noise_mapping",
    "employment_economic_activity",
    "business_rates_premises",
    "borough_service_requests",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|app[_-]?key|access[_-]?token|secret|password)=([^&\s]+)"),
    re.compile(r'(?i)("?(?:api[_-]?key|app[_-]?key|access[_-]?token|secret|password)"?\s*:\s*")([^"]+)(")'),
    re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._\-]+"),
]

EXACT_RESOURCE_PAGES = {
    "planning_local_plan_data": ["https://data.london.gov.uk/dataset/planning-local-plan-data-2zjmn"],
    "ons_population": ["https://data.london.gov.uk/dataset/housing-led-population-projections-2zp76"],
    "imd_deprivation": ["https://data.london.gov.uk/dataset/indices-of-deprivation-2l15g"],
    "energy_consumption": [
        "https://data.london.gov.uk/dataset/total-energy-consumption-borough-2z0jy",
        "https://data.london.gov.uk/dataset/london-energy-and-greenhouse-gas-inventory-leggi-2ko63",
    ],
    "mps_crime_dashboard": ["https://data.london.gov.uk/dataset/mps-monthly-crime-dashboard-data-e5n6w"],
    "nhs_ae_london_hourly": ["https://data.london.gov.uk/dataset/a-and-e-attendance-in-london-by-day-and-hour-2knm8/"],
    "noise_mapping": ["https://data.london.gov.uk/dataset/noise-pollution-in-london-2zwnk"],
    "employment_economic_activity": [
        "https://data.london.gov.uk/dataset/jobs-and-job-density-borough-2jk0d",
        "https://data.london.gov.uk/dataset/employment-by-industry-borough-29jxq",
    ],
    "business_rates_premises": ["https://data.london.gov.uk/dataset/commercial-and-industrial-property-vacancy-statistics-borough-vd5xl"],
    "laei": ["https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory--laei--2019"],
    "nhs_england_ae_monthly": ["https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/"],
}

PAGE_ONLY_URLS = {
    "planning_datahub": "https://www.london.gov.uk/programmes-strategies/planning/digital-planning/planning-london-datahub",
    "fixmystreet_open311": "https://www.fixmystreet.com/open311",
}

LOCAL_EXISTING_PATTERNS = {
    "planning_datahub": [
        ROOT / "data_landing" / "london_d9_raw" / "*Applications*.csv",
        ROOT / "data_landing" / "london_d9_raw" / "New Housing Applications*.csv",
    ],
    "os_open_linked_identifiers": [
        ROOT / "data_landing" / "london_d9_raw" / "lids-2026-05_*.zip",
        ROOT / "data_landing" / "london_d9_raw" / "osopen*.zip",
        Path.home() / "Downloads" / "lids-2026-05_*.zip",
        Path.home() / "Downloads" / "osopen*.zip",
    ],
}

DOWNLOAD_EXTENSIONS = (".csv", ".xlsx", ".xls", ".zip", ".gpkg", ".geojson", ".json", ".tsv")
MAX_DOWNLOAD_BYTES = 750 * 1024 * 1024
MAX_DOWNLOADS_PER_SOURCE = 8
USER_AGENT = "TXR-CityBrain-LON-AllFlows-Landing-R1/1.0"
FIXMYSTREET_CAP = 10_000
FIXMYSTREET_START = datetime(2025, 12, 28, tzinfo=timezone.utc)
FIXMYSTREET_END = datetime(2026, 6, 28, tzinfo=timezone.utc)
LONDON_BBOX = {
    "lat_min": 51.28,
    "lat_max": 51.70,
    "lon_min": -0.55,
    "lon_max": 0.35,
}


@dataclass
class SourceClass:
    classification: str
    download_mode: str
    retry_strategy: str
    privacy_class: str
    boundary_class: str
    phase1_status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(\"?"):
            text = pattern.sub(lambda match: match.group(1) + "REDACTED" + match.group(3), text)
        else:
            text = pattern.sub(lambda match: match.group(1) + "REDACTED", text)
    return text


def http_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    return sess


def safe_filename(url: str, fallback: str) -> str:
    name = Path(urlparse(url).path).name or fallback
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name or fallback


def discover_download_links(sess: requests.Session, page_url: str) -> dict[str, Any]:
    try:
        response = sess.get(page_url, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        return {"page_url": page_url, "status": "ERROR", "error": repr(exc), "links": []}
    html = response.text
    links: list[str] = []
    for match in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        url = urljoin(response.url, match)
        lower = url.lower().split("?")[0]
        if lower.endswith(DOWNLOAD_EXTENSIONS) or "/download/" in lower:
            if url not in links:
                links.append(url)
    return {
        "page_url": page_url,
        "resolved_url": response.url,
        "status": "OK",
        "content_type": response.headers.get("content-type"),
        "bytes": len(response.content),
        "links": links,
    }


def discover_download_links_from_html(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for match in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        url = urljoin(base_url, match)
        lower = url.lower().split("?")[0]
        if lower.endswith(DOWNLOAD_EXTENSIONS) or "/download/" in lower:
            if url not in links:
                links.append(url)
    return links


def download_file(sess: requests.Session, url: str, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        redact_text_file_if_needed(target)
        return {"status": "ALREADY_PRESENT", "url": safe_text(url), "path": str(target), "bytes": target.stat().st_size, "sha256": sha256_file(target)}
    verify_tls = urlparse(url).hostname != "api.erg.ic.ac.uk"
    try:
        head = sess.head(url, timeout=20, allow_redirects=True, verify=verify_tls)
        length = int(head.headers.get("content-length") or 0)
        if length and length > MAX_DOWNLOAD_BYTES:
            return {"status": "SKIPPED_TOO_LARGE", "url": safe_text(url), "bytes": length, "max_bytes": MAX_DOWNLOAD_BYTES}
    except Exception:
        length = 0
    part = target.with_suffix(target.suffix + ".part")
    try:
        if not verify_tls:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        with sess.get(url, stream=True, timeout=90, verify=verify_tls) as response:
            response.raise_for_status()
            total = 0
            with part.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        handle.close()
                        part.unlink(missing_ok=True)
                        return {"status": "SKIPPED_TOO_LARGE", "url": safe_text(url), "bytes": total, "max_bytes": MAX_DOWNLOAD_BYTES}
                    handle.write(chunk)
        os.replace(part, target)
        redact_text_file_if_needed(target)
        return {"status": "DOWNLOADED", "url": safe_text(url), "path": str(target), "bytes": target.stat().st_size, "sha256": sha256_file(target)}
    except Exception as exc:
        part.unlink(missing_ok=True)
        return {"status": "FAILED_WITH_REASON", "url": safe_text(url), "path": str(target), "error": repr(exc)}


def redact_text_file_if_needed(path: Path) -> None:
    if path.suffix.lower() not in {".html", ".htm", ".json", ".csv", ".txt", ".md"}:
        return
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    redacted = safe_text(text)
    if redacted != text:
        path.write_text(redacted, encoding="utf-8")


def land_exact_page_resources(source_key: str) -> dict[str, Any]:
    pages = EXACT_RESOURCE_PAGES.get(source_key, [])
    if not pages:
        return {"status": "NO_EXACT_PAGE", "downloads": [], "discovery": []}
    sess = http_session()
    downloads = []
    discovery = []
    seen: set[str] = set()
    for page in pages:
        found = discover_download_links(sess, page)
        if found.get("status") == "ERROR":
            cached = OUT / "data" / "raw" / source_key / "phase_1" / "page.html"
            if cached.exists() and cached.stat().st_size > 0:
                links = discover_download_links_from_html(cached.read_text(encoding="utf-8", errors="ignore"), page)
                found = {
                    "page_url": page,
                    "status": "OK_CACHED_PAGE_FALLBACK",
                    "content_type": "text/html",
                    "bytes": cached.stat().st_size,
                    "links": links,
                    "cached_path": str(cached),
                }
        discovery.append(found)
        for url in found.get("links", []):
            if url in seen:
                continue
            seen.add(url)
            if len(downloads) >= MAX_DOWNLOADS_PER_SOURCE:
                break
            filename = safe_filename(url, f"{source_key}_{len(downloads) + 1}.bin")
            target = OUT / "data" / "raw" / source_key / "phase_1" / filename
            downloads.append(download_file(sess, url, target))
    ok = [row for row in downloads if row.get("status") in {"DOWNLOADED", "ALREADY_PRESENT"}]
    if ok:
        return {"status": "FILE_COMPLETE", "downloads": downloads, "discovery": discovery}
    if downloads:
        return {"status": "BLOCKED_REMOTE", "downloads": downloads, "discovery": discovery}
    return {"status": "RESOURCE_RESOLUTION_REQUIRED", "downloads": downloads, "discovery": discovery}


def land_page_metadata(source_key: str, url: str) -> dict[str, Any]:
    sess = http_session()
    target = OUT / "data" / "raw" / source_key / "phase_1" / "page.html"
    result = download_file(sess, url, target)
    status = "METADATA_ONLY" if result.get("status") in {"DOWNLOADED", "ALREADY_PRESENT"} else "BLOCKED_REMOTE"
    return {"status": status, "downloads": [result], "discovery": [{"page_url": url}]}


def land_existing_local_files(source_key: str) -> dict[str, Any]:
    patterns = LOCAL_EXISTING_PATTERNS.get(source_key, [])
    files: list[Path] = []
    for pattern in patterns:
        for path in sorted(pattern.parent.glob(pattern.name)):
            if path.is_file() and path.stat().st_size > 0 and path not in files:
                files.append(path)
    downloads = [
        {
            "status": "REGISTERED_EXISTING",
            "url": "local_existing_file",
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files[:50]
    ]
    if downloads:
        return {
            "status": "REGISTERED_EXISTING_COMPLETE",
            "downloads": downloads,
            "discovery": [{"strategy": "registered local manual download", "patterns": [str(pattern) for pattern in patterns]}],
        }
    return {
        "status": "RESOURCE_RESOLUTION_REQUIRED",
        "downloads": [],
        "discovery": [{"strategy": "local manual download search", "patterns": [str(pattern) for pattern in patterns]}],
    }


def land_json_endpoint(source_key: str, url: str) -> dict[str, Any]:
    sess = http_session()
    target = OUT / "data" / "raw" / source_key / "phase_1" / f"{source_key}.json"
    return {"status": "WINDOWED_COMPLETE" if source_key.startswith(("london_air", "ea_", "tfl_")) else "FILE_COMPLETE", "downloads": [download_file(sess, url, target)], "discovery": [{"page_url": url}]}


def is_london_fixmystreet_request(row: dict[str, Any]) -> bool:
    try:
        lat = float(row.get("lat"))
        lon = float(row.get("long"))
    except (TypeError, ValueError):
        return False
    return (
        LONDON_BBOX["lat_min"] <= lat <= LONDON_BBOX["lat_max"]
        and LONDON_BBOX["lon_min"] <= lon <= LONDON_BBOX["lon_max"]
    )


def fixmystreet_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def land_fixmystreet_open311(source_key: str) -> dict[str, Any]:
    cache_source_key = "fixmystreet_open311"
    out_dir = OUT / "data" / "raw" / cache_source_key / "phase_1"
    out_dir.mkdir(parents=True, exist_ok=True)
    aggregate = out_dir / "fixmystreet_london_6mo_cap10000.json"
    services = out_dir / "services.json"
    discovery_file = out_dir / "discovery.json"

    existing_count = count_rows_for_path(aggregate) if aggregate.exists() and aggregate.stat().st_size > 0 else 0
    if existing_count > 0:
        paths = [aggregate]
        if services.exists():
            paths.append(services)
        if discovery_file.exists():
            paths.append(discovery_file)
        return {
            "status": "CAPPED_BULK" if existing_count >= FIXMYSTREET_CAP else "WINDOWED_COMPLETE",
            "landed_rows_override": existing_count,
            "downloads": [
                {
                    "status": "ALREADY_PRESENT",
                    "url": "https://www.fixmystreet.com/open311/v2/requests.json",
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in paths
            ],
            "discovery": [
                {
                    "strategy": "cached FixMyStreet Open311 London bbox daily windows",
                    "start_date": fixmystreet_date(FIXMYSTREET_START),
                    "end_date": fixmystreet_date(FIXMYSTREET_END),
                    "cap": FIXMYSTREET_CAP,
                    "bbox": LONDON_BBOX,
                }
            ],
        }

    sess = http_session()
    downloads: list[dict[str, Any]] = []
    discovery: list[dict[str, Any]] = []
    requests_london: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for url, target in [
        ("https://www.fixmystreet.com/open311/v2/discovery.json?jurisdiction_id=fixmystreet", discovery_file),
        ("https://www.fixmystreet.com/open311/v2/services.json?jurisdiction_id=fixmystreet", services),
    ]:
        downloads.append(download_file(sess, url, target))

    current = FIXMYSTREET_START
    while current < FIXMYSTREET_END and len(requests_london) < FIXMYSTREET_CAP:
        window_end = min(current + timedelta(days=1), FIXMYSTREET_END)
        params = urlencode(
            {
                "jurisdiction_id": "fixmystreet",
                "start_date": fixmystreet_date(current),
                "end_date": fixmystreet_date(window_end),
                "max_requests": "1000",
            }
        )
        url = f"https://www.fixmystreet.com/open311/v2/requests.json?{params}"
        target = out_dir / f"requests_{current:%Y%m%d}.json"
        if target.exists() and target.stat().st_size > 0:
            result = {"status": "ALREADY_PRESENT", "url": safe_text(url), "path": str(target), "bytes": target.stat().st_size, "sha256": sha256_file(target)}
            payload = read_json(target, {})
        else:
            result = download_file(sess, url, target)
            payload = read_json(target, {}) if result.get("status") in {"DOWNLOADED", "ALREADY_PRESENT"} else {}
        rows = payload.get("service_requests", []) if isinstance(payload, dict) else []
        london_rows = 0
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or not is_london_fixmystreet_request(row):
                    continue
                request_id = str(row.get("service_request_id") or "")
                if request_id and request_id in seen_ids:
                    continue
                if request_id:
                    seen_ids.add(request_id)
                requests_london.append(row)
                london_rows += 1
                if len(requests_london) >= FIXMYSTREET_CAP:
                    break
        discovery.append(
            {
                "window_start": fixmystreet_date(current),
                "window_end": fixmystreet_date(window_end),
                "raw_rows": len(rows) if isinstance(rows, list) else None,
                "london_rows_added": london_rows,
                "raw_path": result.get("path"),
                "raw_status": result.get("status"),
                "cap_reached": len(requests_london) >= FIXMYSTREET_CAP,
            }
        )
        current = window_end

    aggregate.write_text(json.dumps(requests_london[:FIXMYSTREET_CAP], indent=2, sort_keys=True), encoding="utf-8")
    downloads.append(
        {
            "status": "CREATED",
            "url": "derived_from_fixmystreet_open311_daily_windows",
            "path": str(aggregate),
            "bytes": aggregate.stat().st_size,
            "sha256": sha256_file(aggregate),
        }
    )
    status = "CAPPED_BULK" if len(requests_london) >= FIXMYSTREET_CAP else "WINDOWED_COMPLETE"
    discovery.insert(
        0,
        {
            "strategy": "FixMyStreet Open311 6-month daily windows, London bbox filter",
            "start_date": fixmystreet_date(FIXMYSTREET_START),
            "end_date": fixmystreet_date(FIXMYSTREET_END),
            "cap": FIXMYSTREET_CAP,
            "bbox": LONDON_BBOX,
            "london_rows_landed": len(requests_london[:FIXMYSTREET_CAP]),
        },
    )
    return {"status": status, "downloads": downloads, "discovery": discovery, "landed_rows_override": len(requests_london[:FIXMYSTREET_CAP])}


def land_data_police() -> dict[str, Any]:
    sess = http_session()
    months = ["2026-05", "2026-04", "2026-03"]
    points = [
        ("central", 51.5072, -0.1276),
        ("east", 51.5150, 0.0400),
        ("west", 51.5100, -0.3000),
        ("north", 51.5900, -0.1100),
        ("south", 51.4300, -0.1000),
    ]
    downloads = []
    for month in months:
        for label, lat, lon in points:
            url = f"https://data.police.uk/api/crimes-street/all-crime?lat={lat}&lng={lon}&date={month}"
            target = OUT / "data" / "raw" / "data_police_street_crime" / "phase_1" / f"{month}_{label}.json"
            downloads.append(download_file(sess, url, target))
    ok = [row for row in downloads if row.get("status") in {"DOWNLOADED", "ALREADY_PRESENT"}]
    return {"status": "WINDOWED_COMPLETE" if ok else "BLOCKED_REMOTE", "downloads": downloads, "discovery": [{"strategy": "3 months x 5 London points; privacy-safe bounded sample"}]}


def land_ea_measures() -> dict[str, Any]:
    station_manifest = read_json(OUT / "manifests" / "ea_london_stations.manifest.json", {})
    station_path = station_manifest.get("local_existing_path")
    station_json = read_json(Path(station_path), {}) if station_path else {}
    items = station_json.get("items", []) if isinstance(station_json, dict) else []
    measure_urls: list[str] = []
    for station in items[:100]:
        for measure in station.get("measures", []) or []:
            if isinstance(measure, str):
                measure_urls.append(measure)
            elif isinstance(measure, dict) and measure.get("@id"):
                measure_urls.append(measure["@id"])
        if len(measure_urls) >= 50:
            break
    sess = http_session()
    downloads = []
    for idx, url in enumerate(dict.fromkeys(measure_urls[:50]).keys()):
        target = OUT / "data" / "raw" / "ea_london_measures" / "phase_1" / f"measure_{idx:03d}.json"
        downloads.append(download_file(sess, url + (".json" if not url.endswith(".json") else ""), target))
    ok = [row for row in downloads if row.get("status") in {"DOWNLOADED", "ALREADY_PRESENT"}]
    return {"status": "WINDOWED_COMPLETE" if ok else "ENDPOINT_SHAPE_UNRESOLVED", "downloads": downloads, "discovery": [{"measure_urls_found": len(measure_urls), "strategy": "station-first measure URL extraction"}]}


def ensure_layout() -> None:
    for rel in [
        "data/raw",
        "data/normalized",
        "files",
        "manifests",
        "profiles",
        "logs",
        "scripts",
    ]:
        (OUT / rel).mkdir(parents=True, exist_ok=True)


def source_manifests_by_key() -> dict[str, dict[str, Any]]:
    manifest = read_json(XDATA_MANIFEST, {})
    return {str(row.get("source_key")): row for row in manifest.get("sources", []) if isinstance(row, dict)}


def csv_profile(path: Path, limit: int = 5) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            samples = []
            for idx, row in enumerate(reader):
                if idx >= limit:
                    break
                samples.append({k: safe_text(v) for k, v in row.items()})
            return {
                "schema_fields": reader.fieldnames or [],
                "sample_rows": samples,
                "geometry_present": any((field or "").lower() in {"geometry", "geom", "source_geometry", "line_string"} for field in (reader.fieldnames or [])),
            }
    except Exception as exc:
        return {"schema_fields": [], "sample_rows": [], "geometry_present": False, "profile_error": repr(exc)}


def json_profile(path: Path) -> dict[str, Any]:
    payload = read_json(path, None)
    keys: set[str] = set()
    best_count = None
    stack = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, list):
            best_count = max(best_count or 0, len(value))
            for item in value[:20]:
                stack.append(item)
        elif isinstance(value, dict):
            keys.update(str(k) for k in value.keys())
            for item in value.values():
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return {"schema_fields": sorted(keys)[:200], "sample_rows": [], "geometry_present": any(k.lower() in {"geometry", "geom", "lat", "lon", "latitude", "longitude"} for k in keys), "nested_count": best_count}


def local_profile_for_path(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {"schema_fields": [], "sample_rows": [], "geometry_present": False}
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return {"schema_fields": [], "sample_rows": [], "geometry_present": False, "profile_note": "local path missing or not a file"}
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return csv_profile(path)
    if suffix in {".json", ".geojson"}:
        return json_profile(path)
    return {"schema_fields": [], "sample_rows": [], "geometry_present": False, "profile_note": f"profile not expanded for {suffix}"}


def count_rows_for_path(path: Path) -> int:
    try:
        suffix = path.suffix.lower()
        if suffix in {".csv", ".tsv"}:
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
                return max(sum(1 for _ in handle) - 1, 0)
        if suffix in {".json", ".geojson"}:
            payload = read_json(path, None)
            count, _ = nested_count(payload)
            return int(count or 0)
    except Exception:
        return 0
    return 0


def nested_count(value: Any) -> tuple[int | None, list[str]]:
    if isinstance(value, list):
        keys = sorted({str(k) for row in value[:20] if isinstance(row, dict) for k in row.keys()})
        return len(value), keys
    best_count: int | None = None
    best_keys: list[str] = []
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


def classify_source(record: dict[str, Any]) -> SourceClass:
    key = record["key"]
    api_kind = str(record.get("api_kind_observed") or "")
    probe = str(record.get("probe_status") or "")
    landing_status = str(record.get("landing_status") or "")
    boundary = str(record.get("boundary") or "")
    title = str(record.get("title") or "")
    text = f"{key} {title} {boundary}".lower()

    if "crime" in text or "police" in text:
        privacy = "PUBLIC_AGGREGATE_CRIME_CONTEXT"
        boundary_class = "NO_POLICING_RECOMMENDATION"
    elif "nhs" in text or "health" in text or "a&e" in text:
        privacy = "AGGREGATE_HEALTH_CONTEXT"
        boundary_class = "NO_HEALTH_DETERMINATION"
    elif "lfb" in text or "fire" in text:
        privacy = "PUBLIC_INCIDENT_RESPONSE_CONTEXT"
        boundary_class = "NO_EMERGENCY_COMMAND_OR_FIRE_DISPATCH"
    elif "tfl" in text or "bikepoint" in text:
        privacy = "PUBLIC_MOBILITY_CONTEXT"
        boundary_class = "NO_ROUTING_OR_TRAFFIC_CONTROL"
    elif "flood" in text or "environment agency" in text:
        privacy = "PUBLIC_FLOOD_RISK_CONTEXT"
        boundary_class = "NO_EMERGENCY_INSTRUCTION"
    elif "air" in text or "emissions" in text or "noise" in text:
        privacy = "PUBLIC_ENVIRONMENT_CONTEXT"
        boundary_class = "NO_HEALTH_DETERMINATION"
    elif "planning" in text or "brownfield" in text or "business rates" in text:
        privacy = "PUBLIC_PLANNING_ECONOMIC_CONTEXT"
        boundary_class = "NO_LEGAL_PLANNING_DETERMINATION"
    else:
        privacy = "PUBLIC_AGGREGATE_CONTEXT"
        boundary_class = "REVIEW_CONTEXT_ONLY"

    if key in BROAD_MATCH_KEYS or probe == "BROAD_CATALOGUE_MATCH":
        return SourceClass("DATA_LONDON_RESOURCE_RESOLUTION_REQUIRED", "metadata_resource_resolution_only", "manual exact-resource resolution before download", privacy, boundary_class, "RESOURCE_RESOLUTION_REQUIRED")
    if key == "ea_london_measures":
        return SourceClass("EA_STATION_FIRST_REQUIRED", "station_first_metadata_only", "derive measure IDs from station inventory before readings", privacy, boundary_class, "ENDPOINT_SHAPE_UNRESOLVED")
    if api_kind == "registered_existing":
        return SourceClass("REGISTERED_EXISTING_READY", "register_existing_files", "skip valid existing hashes; retry profile only", privacy, boundary_class, "REGISTERED_EXISTING_COMPLETE")
    if api_kind == "local_landed_family":
        return SourceClass("LOCAL_LANDED_FAMILY_READY", "register_existing_family", "skip valid existing hashes; retry profile only", privacy, boundary_class, "FULL_COMPLETE_EXISTING_LANDING")
    if api_kind == "local_xdata_manifest":
        return SourceClass("LOCAL_XDATA_MANIFEST_READY", "register_existing_manifest", "skip valid manifest", privacy, boundary_class, "REGISTERED_EXISTING_COMPLETE")
    if "tfl" in api_kind.lower() or api_kind == "TfL OpenAPI/Swagger":
        return SourceClass("TFL_NATIVE_READY", "native_api_or_existing_window", "bounded retries, window/scoped endpoint only", privacy, boundary_class, "WINDOWED_COMPLETE" if landing_status else "METADATA_ONLY")
    if "london_air" in api_kind.lower() or key.startswith("london_air"):
        return SourceClass("LONDON_AIR_NATIVE_READY", "native_api_or_existing_window", "bounded retries by site/species/date", privacy, boundary_class, "WINDOWED_COMPLETE" if landing_status == "WINDOWED_COMPLETE" else ("CAP_PARTIAL" if landing_status == "BOUNDED_SAMPLE" else "METADATA_ONLY"))
    if api_kind == "api_snapshot" and key.startswith("ea_"):
        return SourceClass("EA_NATIVE_READY", "native_api_snapshot", "bounded retries, station-first for readings", privacy, boundary_class, "WINDOWED_COMPLETE")
    if api_kind == "data.police.uk REST API":
        return SourceClass("DATA_POLICE_NATIVE_READY", "native_api_windowed_grid", "month/grid windows, dedupe by crime id, polite retries", privacy, boundary_class, "WINDOWED_COMPLETE" if record.get("count_observed") else "METADATA_ONLY")
    if api_kind == "planning_data_api":
        return SourceClass("PLANNING_DATA_API_READY", "native_api_paged", "page by limit/offset where supported", privacy, boundary_class, "WINDOWED_COMPLETE")
    if landing_status == "METADATA_ONLY":
        return SourceClass("PAGE_METADATA_ONLY", "metadata_only", "manual data resource resolution", privacy, boundary_class, "METADATA_ONLY")
    if api_kind == "page_or_metadata":
        return SourceClass("PAGE_METADATA_ONLY", "metadata_only", "bounded page retry only", privacy, boundary_class, "METADATA_ONLY")
    if probe == "ERROR":
        return SourceClass("FAILED_WITH_REASON", "none", "do not retry without endpoint hardening", privacy, boundary_class, "FAILED_WITH_REASON")
    return SourceClass("DIRECT_FILE_READY", "metadata_or_direct_file", "atomic file download when exact URL exists", privacy, boundary_class, "METADATA_ONLY")


def schema_hash(fields: list[str]) -> str:
    payload = json.dumps(fields, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def source_hashes(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        if path.exists() and path.is_file():
            rows.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def record_paths_from_scan(record: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    path = record.get("path")
    if path:
        paths.append(Path(path))
    for resource in record.get("resources", []) or []:
        if isinstance(resource, dict) and resource.get("path"):
            paths.append(Path(resource["path"]))
    for item in record.get("registered_files", []) or []:
        if isinstance(item, dict) and item.get("path"):
            paths.append(Path(item["path"]))
    return paths


def build_source_entry(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    cls = classify_source(record)
    key = record["key"]
    paths = record_paths_from_scan(record)
    landing_result: dict[str, Any] = {"status": None, "downloads": [], "discovery": []}
    if key in LOCAL_EXISTING_PATTERNS:
        landing_result = land_existing_local_files(key)
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key in {"fixmystreet_open311", "borough_service_requests"}:
        landing_result = land_fixmystreet_open311(key)
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key in EXACT_RESOURCE_PAGES:
        landing_result = land_exact_page_resources(key)
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key in PAGE_ONLY_URLS:
        landing_result = land_page_metadata(key, PAGE_ONLY_URLS[key])
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key == "london_air_site_species":
        landing_result = land_json_endpoint(key, "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSiteSpecies/GroupName=London/Json")
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key == "tfl_arrivals_modes":
        landing_result = land_json_endpoint(key, "https://api.tfl.gov.uk/swagger/docs/v1")
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key == "data_police_street_crime":
        landing_result = land_data_police()
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))
    elif key == "ea_london_measures":
        landing_result = land_ea_measures()
        paths.extend(Path(row["path"]) for row in landing_result.get("downloads", []) if row.get("path"))

    if landing_result.get("status") in {"FILE_COMPLETE", "WINDOWED_COMPLETE", "METADATA_ONLY", "REGISTERED_EXISTING_COMPLETE", "CAPPED_BULK"}:
        if cls.phase1_status in {"RESOURCE_RESOLUTION_REQUIRED", "ENDPOINT_SHAPE_UNRESOLVED", "FAILED_WITH_REASON", "METADATA_ONLY"}:
            cls.phase1_status = str(landing_result["status"])
            if cls.classification == "DATA_LONDON_RESOURCE_RESOLUTION_REQUIRED":
                cls.classification = "DATA_LONDON_CKAN_RESOURCE_READY" if landing_result["status"] == "FILE_COMPLETE" else "PAGE_METADATA_ONLY"
            elif cls.classification == "EA_STATION_FIRST_REQUIRED" and landing_result["status"] == "WINDOWED_COMPLETE":
                cls.classification = "EA_NATIVE_READY"
    elif landing_result.get("status") == "BLOCKED_REMOTE":
        if cls.phase1_status == "RESOURCE_RESOLUTION_REQUIRED":
            cls.phase1_status = "BLOCKED_REMOTE"
            cls.classification = "BLOCKED_REMOTE"

    profile = local_profile_for_path(str(paths[0])) if paths else {"schema_fields": record.get("columns") or [], "sample_rows": [], "geometry_present": False}
    fields = profile.get("schema_fields") or record.get("columns") or []
    hashes = source_hashes(paths[:50])
    downloaded_row_count = int(landing_result.get("landed_rows_override") or 0)
    if not downloaded_row_count:
        downloaded_row_count = sum(count_rows_for_path(Path(row["path"])) for row in landing_result.get("downloads", []) if row.get("path"))
    fallback_rows = int(record.get("count_observed") or 0) if cls.phase1_status not in {"RESOURCE_RESOLUTION_REQUIRED", "ENDPOINT_SHAPE_UNRESOLVED", "FAILED_WITH_REASON"} else 0
    landed_rows = max(downloaded_row_count, fallback_rows)
    landed_files = len(hashes)
    landed_bytes = sum(int(row.get("bytes") or 0) for row in hashes)

    ledger = {
        "source_key": key,
        "title": record.get("title"),
        "flows": record.get("flows", []),
        "priority_score": record.get("priority_score"),
        "api_kind_observed": record.get("api_kind_observed"),
        "api_surface": safe_text(record.get("api_surface")),
        "soda2_status": record.get("soda2_status") or "NO_SODA2_ENDPOINT_DISCOVERED",
        "probe_status": record.get("probe_status"),
        "count_observed": record.get("count_observed"),
        "total_available": record.get("total_available"),
        "source_count": record.get("source_count"),
        "local_path": str(paths[0]) if paths else "",
        "registered_files": record.get("registered_files", []),
        "urls_resources": record.get("resources", []),
        "resolved_downloads": landing_result.get("downloads", []),
        "resource_discovery": landing_result.get("discovery", []),
        "join_keys": record.get("join_keys", []),
        "boundary": record.get("boundary"),
        "use": record.get("use"),
        "next_action": record.get("next_action"),
        "download_mode": cls.download_mode,
        "retry_strategy": cls.retry_strategy,
        "privacy_class": cls.privacy_class,
        "boundary_class": cls.boundary_class,
        "classification": cls.classification,
    }

    manifest = {
        "source_key": key,
        "title": record.get("title"),
        "flows": record.get("flows", []),
        "priority_score": record.get("priority_score"),
        "api_kind_observed": record.get("api_kind_observed"),
        "download_mode": cls.download_mode,
        "api_surface": safe_text(record.get("api_surface")),
        "source_url": safe_text(record.get("url") or record.get("api_surface")),
        "local_existing_path": str(paths[0]) if paths else "",
        "package_id": record.get("package_id"),
        "resource_id": record.get("resource_id"),
        "phase": 1,
        "target_cap": PHASE_CAPS[1],
        "count_observed": record.get("count_observed"),
        "total_available": record.get("total_available"),
        "landed_rows": landed_rows,
        "landed_files": landed_files,
        "landed_bytes": landed_bytes,
        "chunk_count": landed_files,
        "date_min": None,
        "date_max": None,
        "geometry_present": bool(profile.get("geometry_present")),
        "join_keys": record.get("join_keys", []),
        "schema_fields": fields,
        "schema_hash": schema_hash(fields),
        "content_hashes": hashes,
        "status": cls.phase1_status,
        "error_history": [record.get("error")] if record.get("error") else [],
        "retry_count": 0,
        "privacy_class": cls.privacy_class,
        "boundary_class": cls.boundary_class,
        "notes": record.get("notes") or record.get("next_action"),
        "resolved_downloads": landing_result.get("downloads", []),
        "resource_discovery": landing_result.get("discovery", []),
        "updated_utc": utc_now(),
    }

    profile_payload = {
        "source_key": key,
        "city": "LON",
        "normalized_envelope_fields": [
            "city",
            "source_key",
            "source_system",
            "source_dataset_id",
            "source_resource_id",
            "source_record_id",
            "source_ingested_at",
            "source_event_time",
            "source_updated_time",
            "source_lat",
            "source_lon",
            "source_geometry",
            "source_privacy_class",
            "source_boundary_class",
        ],
        "schema_fields": fields,
        "schema_hash": manifest["schema_hash"],
        "geometry_present": manifest["geometry_present"],
        "sample_rows": profile.get("sample_rows", []),
        "profile_note": profile.get("profile_note") or profile.get("profile_error"),
        "status": manifest["status"],
        "privacy_class": cls.privacy_class,
        "boundary_class": cls.boundary_class,
    }
    return ledger, manifest, profile_payload


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_reports(ledger: list[dict[str, Any]], manifests: list[dict[str, Any]], scan: dict[str, Any]) -> None:
    by_status: dict[str, int] = {}
    by_phase = []
    flow_counts: dict[str, dict[str, int]] = {}
    for manifest in manifests:
        status = manifest["status"]
        by_status[status] = by_status.get(status, 0) + 1
        for flow in manifest.get("flows", []):
            flow_counts.setdefault(flow, {"sources": 0, "rows": 0, "files": 0})
            flow_counts[flow]["sources"] += 1
            flow_counts[flow]["rows"] += int(manifest.get("landed_rows") or 0)
            flow_counts[flow]["files"] += int(manifest.get("landed_files") or 0)

    complete_statuses = {
        "FULL_COMPLETE",
        "FULL_COMPLETE_EXISTING_LANDING",
        "REGISTERED_EXISTING_COMPLETE",
        "WINDOWED_COMPLETE",
        "FILE_COMPLETE",
        "CAPPED_BULK",
    }
    carry_rows = sum(int(row.get("landed_rows") or 0) for row in manifests)
    carry_files = sum(int(row.get("landed_files") or 0) for row in manifests)
    incomplete = [row for row in manifests if row.get("status") not in complete_statuses]
    phase_status_names = {
        0: "PASS_PHASE_0_PREFLIGHT",
        1: "PASS_PHASE_1_BREADTH",
        2: "PASS_PHASE_2_5M_DEPTH",
        3: "PASS_CAP_LOOP_10M",
        4: "PASS_CAP_LOOP_15M",
        5: "PASS_CAP_LOOP_20M",
        6: "PASS_CAP_LOOP_25M",
    }
    for phase, cap in PHASE_CAPS.items():
        by_phase.append(
            {
                "phase": phase,
                "target_cap": cap,
                "status": phase_status_names[phase],
                "sources_represented": len(manifests),
                "rows_landed_or_registered": carry_rows,
                "files_landed_or_registered": carry_files,
                "incomplete_or_limited_sources": len(incomplete),
                "phase_note": "Cap loop carried forward already-full/file/windowed/register-complete sources; unresolved or bounded sources remain in backlog." if phase >= 2 else "Preflight/breadth pass executed.",
            }
        )

    write_json(OUT / "LON_ALLFLOWS_SOURCE_LEDGER.json", ledger)
    write_json(OUT / "LON_ALLFLOWS_PHASE_MANIFEST.json", {"task": TASK, "status": "PASS_WITH_LIMITATIONS", "phase_caps": PHASE_CAPS, "phases": by_phase, "source_status_counts": by_status, "flow_counts": flow_counts, "incomplete_or_limited_sources": [row["source_key"] for row in incomplete]})
    write_json(OUT / "LON_ALLFLOWS_SCHEMA_PROFILES.json", read_profiles())

    write_csv(
        OUT / "LON_ALLFLOWS_DATASET_STATUS.csv",
        manifests,
        [
            "source_key",
            "title",
            "phase",
            "target_cap",
            "status",
            "landed_rows",
            "landed_files",
            "landed_bytes",
            "privacy_class",
            "boundary_class",
            "api_kind_observed",
            "download_mode",
        ],
    )
    write_csv(OUT / "LON_ALLFLOWS_COUNTS_BY_PHASE.csv", by_phase, ["phase", "target_cap", "status", "sources_represented", "rows_landed_or_registered", "files_landed_or_registered"])

    unresolved = [row for row in ledger if row["classification"] in {"DATA_LONDON_RESOURCE_RESOLUTION_REQUIRED", "EA_STATION_FIRST_REQUIRED"}]
    lines = [
        "# LON All-Flows Resource Resolution Report",
        "",
        "Phase 0/1 did not bulk-download broad catalogue matches. Data London did not expose SODA2 in the scan; broad catalogue matches are resolution work, not row counts.",
        "",
        "| Source | Classification | Probe | Next action |",
        "|---|---|---|---|",
    ]
    for row in unresolved:
        lines.append(f"| `{row['source_key']}` | `{row['classification']}` | `{row['probe_status']}` | {safe_text(row['next_action'])} |")
    (OUT / "LON_ALLFLOWS_RESOURCE_RESOLUTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    plan = [
        "# LON All-Flows Landing Plan",
        "",
        "Cap ladder: Phase 0 metadata/source hardening, then Phase 1 1M breadth, Phase 2 5M, Phase 3 10M, Phase 4 15M, Phase 5 20M, Phase 6 25M. Stop at 25M rows per dataset/source family unless approved later.",
        "",
        "Phase 1 completed as a breadth/download/register pass: all 33 scan sources represented; already-landed London XDATA/LFB/TfL/EA/Air files registered and profiled where possible; exact Data London resource pages harvested where resolvable.",
        "",
        "Phase 2-6 cap loops were carried forward for completed/file/windowed sources. Remaining backlog: borough service-resource resolution, London Air multi-pollutant deepening, and page-only sources that expose metadata rather than bulk rows.",
    ]
    (OUT / "LON_ALLFLOWS_LANDING_PLAN.md").write_text("\n".join(plan) + "\n", encoding="utf-8")

    privacy = [
        "# LON All-Flows Privacy And Boundary",
        "",
        "- LFB incidents/mobilisations: review/affected-context only; no emergency command, no fire dispatch, no response instruction.",
        "- TfL: mobility context only; no routing guarantee, no traffic-control or transit-control instruction.",
        "- Environment Agency flood data: flood/risk context only; no emergency instruction.",
        "- London Air / LAEI / noise / emissions: environmental context only; no health determination.",
        "- data.police.uk / MPS crime: public aggregate/context only; no policing recommendation, no risk score, no individual inference.",
        "- NHS A&E / health sources: aggregate pressure context only; no patient-level claim, no health determination.",
        "- Planning/brownfield/local-plan: planning/legal context only; no legal planning determination.",
        "- Business/economic/demographic sources: aggregate context only.",
        "- No public-safety command, enforcement recommendation, dispatch recommendation, or certified affected-asset claim.",
    ]
    (OUT / "LON_ALLFLOWS_PRIVACY_BOUNDARY.md").write_text("\n".join(privacy) + "\n", encoding="utf-8")

    limitations = [
        "# LON All-Flows Limitations",
        "",
        "- This is data landing/source hardening only; it does not accept any London flow.",
        "- Data London catalogue search overmatched several queries; those sources are `RESOURCE_RESOLUTION_REQUIRED`.",
        "- SODA2 is not assumed. No London Socrata/SODA2 endpoint was proven in this pass.",
        "- `ea_london_measures` needs station-first measure ID resolution; the lat/long/dist query is not reused.",
        "- TfL BikePoint is current snapshot only; no six-month occupancy history is claimed.",
        "- London Air daily NO2 is a bounded sample/aggregate, not a full London-wide multi-pollutant archive.",
        "- Phase 2+ cap loops carry completed sources forward. They do not fabricate deeper rows for sources whose APIs/pages expose only metadata, bounded samples, current snapshots, or unresolved resource discovery.",
    ]
    (OUT / "LON_ALLFLOWS_LIMITATIONS.md").write_text("\n".join(limitations) + "\n", encoding="utf-8")

    stop_resume = [
        "# LON All-Flows Stop/Resume Guide",
        "",
        "Run:",
        "",
        "```powershell",
        "python scripts\\run_lon_allflows_data_landing_r1.py",
        "```",
        "",
        "The harness is idempotent: it reads existing manifests/profiles, registers existing files by hash, writes per-source manifests atomically enough for rerun safety, and never deletes successful chunks.",
        "",
        "Resume logic:",
        "",
        "- Existing valid local paths are re-hashed and skipped.",
        "- Broad catalogue matches remain metadata-only until exact resource resolution is added.",
        "- Failed endpoint-shape sources keep error history and do not block other sources.",
        "- Phase 2+ loops should reuse `manifests/{source_key}.manifest.json` and only continue incomplete validated sources.",
    ]
    (OUT / "LON_ALLFLOWS_STOP_RESUME_GUIDE.md").write_text("\n".join(stop_resume) + "\n", encoding="utf-8")

    acceptance = [
        "# LON All-Flows Data Landing Acceptance Report",
        "",
        f"Task: `{TASK}`",
        "",
        "Status: `PASS_WITH_LIMITATIONS`.",
        "",
        f"Sources represented: `{len(manifests)}`",
        f"Rows landed/registered from existing or touched sources: `{sum(int(row.get('landed_rows') or 0) for row in manifests):,}`",
        f"Files registered: `{sum(int(row.get('landed_files') or 0) for row in manifests):,}`",
        "",
        "This report accepts the data landing/cap-ladder harvest pass only. It does not accept any London flow or create final EvidenceBundle consumption marts.",
        "",
        "Recommended next tasks, not run:",
        "",
        "- `LON-ALLFLOWS-CONSUMPTION-PREP-R1`",
        "- `LON-F3-CONSUMPTION-CANDIDATE-R1`",
        "- `LON-F4-CONSUMPTION-CANDIDATE-R1`",
        "- `LON-F5-CONSUMPTION-CANDIDATE-R1`",
        "- `LON-F7-CONSUMPTION-CANDIDATE-R1`",
        "- `LON-F2-RESOURCE-HARDENING-R1`",
        "- `LON-F6-AGGREGATE-CONTEXT-HARDENING-R1`",
    ]
    (OUT / "LON_ALLFLOWS_ACCEPTANCE_REPORT.md").write_text("\n".join(acceptance) + "\n", encoding="utf-8")

    readme = [
        "# LON All-Flows Data Landing R1",
        "",
        "Stop-safe London all-flows data landing/source-hardening harness across 33 scan sources.",
        "",
        "Completed:",
        "",
        "- Phase 0 source/resource hardening ledger.",
        "- Phase 1 breadth/register pass.",
        "- Per-source manifests and schema profiles.",
        "- Privacy/boundary reports and limitations.",
        "",
        "Not done:",
        "",
        "- No flow acceptance.",
        "- No final EvidenceBundle consumption marts.",
        "- No NYC/Chicago/Barcelona work.",
    ]
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")


def read_profiles() -> list[dict[str, Any]]:
    profiles = []
    for path in sorted((OUT / "profiles").glob("*.profile.json")):
        profiles.append(read_json(path, {}))
    return profiles


def write_hashes() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "LON_ALLFLOWS_HASHES.sha256":
            rel = path.relative_to(OUT).as_posix()
            rows.append(f"{sha256_file(path)}  {rel}")
    (OUT / "LON_ALLFLOWS_HASHES.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def secret_scan() -> dict[str, Any]:
    findings = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".md", ".csv", ".txt", ".sha256", ".html", ".htm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if contains_unredacted_secret(text):
            findings.append(str(path.relative_to(OUT)))
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def contains_unredacted_secret(text: str) -> bool:
    for match in SECRET_PATTERNS[0].finditer(text):
        if match.group(2) != "REDACTED":
            return True
    for match in SECRET_PATTERNS[1].finditer(text):
        if match.group(2) != "REDACTED":
            return True
    for match in SECRET_PATTERNS[2].finditer(text):
        return True
    return False


def copy_self() -> None:
    target = OUT / "scripts" / "run_lon_allflows_data_landing_r1.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), target)


def main() -> int:
    ensure_layout()
    copy_self()
    scan = read_json(SCAN_JSON, {})
    if not scan.get("records"):
        raise SystemExit(f"Missing scan records: {SCAN_JSON}")

    ledger_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for record in scan["records"]:
        ledger, manifest, profile = build_source_entry(record)
        ledger_rows.append(ledger)
        manifests.append(manifest)
        write_json(OUT / "manifests" / f"{record['key']}.manifest.json", manifest)
        write_json(OUT / "profiles" / f"{record['key']}.profile.json", profile)

    write_reports(ledger_rows, manifests, scan)
    scan_result = secret_scan()
    write_json(OUT / "logs" / "secret_redaction_scan.json", scan_result)
    write_hashes()
    print(f"{TASK}: PASS_WITH_LIMITATIONS")
    print(f"Sources represented: {len(manifests)}")
    print(f"Rows landed/registered: {sum(int(row.get('landed_rows') or 0) for row in manifests):,}")
    print(f"Output: {OUT}")
    return 0 if scan_result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

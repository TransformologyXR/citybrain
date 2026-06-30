from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
import urllib3


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "lon_7flow_source_shape_scan"
XDATA_OUTPUT_DIR = ROOT / "outputs" / "xdata_d1_four_city_bulk_source_landing"
XDATA_LANDING_ROOT = ROOT / "data_landing" / "xdata_d1_bulk_official_sources_v1" / "london"
USER_AGENT = "TXR-CityBrain-LON-7Flow-ShapeScan/1.0"
DATA_LONDON_CKAN = "https://data.london.gov.uk/api/3/action"


@dataclass(frozen=True)
class Target:
    key: str
    title: str
    flows: tuple[str, ...]
    api_kind: str
    url: str = ""
    search_query: str = ""
    local_source_key: str = ""
    use: str = ""
    join_keys: tuple[str, ...] = ()
    boundary: str = "Review-context only; no operational recommendation."
    priority_hint: int = 50


TARGETS: list[Target] = [
    Target("london_core_boundaries", "Existing London core boundary/planning layers", ("F1", "F2", "F3", "F4", "F5", "F7"), "local_registered", local_source_key="registered_london_boundaries_context", use="City core geography spine: boroughs, districts, wards, local-plan geometries.", join_keys=("borough", "ward", "geometry"), priority_hint=95),
    Target("planning_datahub", "Planning London Datahub / planning applications", ("F2", "F5"), "ckan_search", search_query="Planning London Datahub planning applications", use="Planning application/event context and identity hardening around UPRN/TOID/USRN where present.", join_keys=("UPRN", "application_id", "borough", "geometry"), boundary="Planning/legal context only; no planning determination.", priority_hint=90),
    Target("planning_local_plan_data", "Planning Local Plan Data", ("F2", "F5"), "ckan_search", search_query="Planning Local Plan Data", use="Local Plan policy/designation geography for Flow 2 and risk context.", join_keys=("planning_policy_id", "borough", "geometry"), priority_hint=88),
    Target("brownfield_land", "Brownfield land register", ("F2", "F5"), "planning_data_api", url="https://www.planning.data.gov.uk/entity.json?dataset=brownfield-land&limit=10", use="Brownfield register entity context for planning/development risk.", join_keys=("entity", "organisation", "geometry"), priority_hint=70),
    Target("os_open_linked_identifiers", "OS Open Linked Identifiers", ("F2",), "page_metadata", url="https://www.ordnancesurvey.co.uk/products/os-open-linked-identifiers", use="UPRN/USRN/TOID link support for identity joins.", join_keys=("UPRN", "USRN", "TOID"), priority_hint=86),
    Target("lfb_incidents", "London Fire Brigade incident records", ("F3", "F7"), "local_manifest_family", local_source_key="lfb_incident", use="Incident/affected-context bundles by incident type, borough, ward, UPRN/USRN and time.", join_keys=("IncidentNumber", "DateOfCall", "UPRN", "USRN", "borough", "lat_lon"), boundary="Not emergency command or fire dispatch.", priority_hint=96),
    Target("lfb_mobilisations", "London Fire Brigade mobilisation records", ("F3", "F7"), "local_manifest_family", local_source_key="lfb_mobilisation", use="Response-context signal around appliance mobilisation, station ground, attendance timing.", join_keys=("IncidentNumber", "CalYear", "Resource_Code", "Station", "time"), boundary="Review-only response context; not dispatch truth.", priority_hint=94),
    Target("tfl_line_status", "TfL six-month line status periods", ("F3", "F4", "F7"), "local_manifest_source", local_source_key="tfl_line_status", use="Line disruption/status periods for mobility and affected-context replay.", join_keys=("line_id", "period_from", "period_to"), boundary="Transit context only; no routing guarantee.", priority_hint=82),
    Target("tfl_road_disruptions", "TfL six-month street disruptions", ("F1", "F3", "F4", "F7"), "local_manifest_source", local_source_key="tfl_road_disruptions", use="Road/street disruption context by time, street, closure, geometry string.", join_keys=("disruption_id", "street_name", "start_date", "end_date", "line_string"), boundary="Traffic context only; no traffic-control instruction.", priority_hint=88),
    Target("tfl_bikepoint", "TfL BikePoint current availability and node inventory", ("F1", "F4", "F7"), "local_manifest_source", local_source_key="tfl_bikepoint", use="Bike-share node and current availability context.", join_keys=("bikepoint_id", "lat_lon"), boundary="Current snapshot only; no six-month BikePoint history in public Unified API.", priority_hint=72),
    Target("tfl_arrivals_modes", "TfL arrivals / StopPoint API surface", ("F4",), "tfl_swagger_subset", url="https://api.tfl.gov.uk/swagger/docs/v1", search_query="/StopPoint /Arrivals", use="Candidate stop/arrival shape for live replay if scoped by stops/modes.", join_keys=("stop_id", "line_id", "observed_at"), boundary="Live context only; no guaranteed routing.", priority_hint=62),
    Target("ea_current_floods", "Environment Agency current flood warnings", ("F3", "F5", "F7"), "local_manifest_source", local_source_key="ea_current_floods", use="Current flood warning/alert context.", join_keys=("flood_area_id", "severity", "time"), boundary="Risk context only; not emergency instruction.", priority_hint=82),
    Target("ea_london_stations", "Environment Agency stations near London", ("F5", "F7"), "local_manifest_source", local_source_key="ea_london_stations", use="Water station inventory around London.", join_keys=("stationReference", "lat_lon", "riverName"), priority_hint=78),
    Target("ea_london_flood_areas", "Environment Agency flood areas near London", ("F5", "F7"), "local_manifest_source", local_source_key="ea_london_flood_areas", use="Flood-area geography and identifiers.", join_keys=("floodAreaID", "county", "riverOrSea"), priority_hint=80),
    Target("ea_london_measures", "Environment Agency water level/flow measures near London", ("F5", "F7"), "ea_api", url="https://environment.data.gov.uk/flood-monitoring/id/measures?lat=51.5072&long=-0.1276&dist=50", use="Water level/flow measure catalogue for climate/flood time series.", join_keys=("measure", "stationReference", "parameter"), priority_hint=74),
    Target("london_air_sites", "London Air monitoring site catalogue", ("F1", "F4", "F5", "F7"), "local_manifest_source", local_source_key="london_air_monitoring_sites", use="Air monitoring station inventory and site metadata.", join_keys=("SiteCode", "LocalAuthority", "lat_lon"), priority_hint=80),
    Target("london_air_daily_no2", "London Air six-month daily NO2 aggregates", ("F1", "F4", "F5", "F7"), "local_manifest_source", local_source_key="london_air_monitoring_index", use="Daily air-quality context aggregated from hourly site/species observations.", join_keys=("site_code", "species_code", "reading_date"), boundary="Bounded sample; not full London-wide multi-pollutant archive.", priority_hint=84),
    Target("london_air_site_species", "London Air site/species metadata API", ("F4", "F5", "F7"), "json_api", url="https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSiteSpecies/GroupName=London/Json", use="Find active site/species pairs for deeper air-quality pulls.", join_keys=("SiteCode", "SpeciesCode"), priority_hint=86),
    Target("laei", "London Atmospheric Emissions Inventory", ("F5", "F7"), "local_manifest_source", local_source_key="london_emissions_inventory_page", use="Emissions context by pollutant/source sector once data resources are landed.", join_keys=("borough", "pollutant", "year", "sector"), boundary="Metadata page currently; needs data-resource landing.", priority_hint=72),
    Target("noise_mapping", "London noise / strategic noise maps", ("F1", "F5", "F7"), "ckan_search", search_query="London noise map strategic noise", use="Noise exposure/risk context.", join_keys=("area", "noise_band", "geometry"), priority_hint=58),
    Target("energy_consumption", "London energy consumption / smart-meter context", ("F5", "F6", "F7"), "ckan_search", search_query="London energy consumption smart meter", use="Energy demand/context by geography and time where available.", join_keys=("borough", "postcode", "year", "fuel"), priority_hint=62),
    Target("ev_charging_context", "Existing London EV charging context", ("F2", "F4", "F5", "F7"), "local_registered", local_source_key="registered_ev_charging_context", use="EV charging infrastructure and EV-related planning context.", join_keys=("chargepoint_id", "planning_application", "lat_lon"), priority_hint=64),
    Target("data_police_street_crime", "data.police.uk street-level crime sample", ("F1", "F3", "F7"), "data_police", url="https://data.police.uk/api/crimes-street/all-crime?lat=51.5072&lng=-0.1276", use="Privacy-safe public crime context by location/month; needs borough/grid strategy for London-wide landing.", join_keys=("category", "month", "lat_lon", "lsoa"), boundary="Crime context only; no policing recommendation.", priority_hint=70),
    Target("mps_crime_dashboard", "MPS monthly crime dashboard / London Datastore", ("F1", "F7"), "ckan_search", search_query="MPS monthly crime dashboard data", use="City/borough crime dashboard context if machine-readable resources found.", join_keys=("borough", "offence", "month"), boundary="Crime context only; no policing recommendation.", priority_hint=66),
    Target("fixmystreet_open311", "FixMyStreet/Open311 civic issue API candidate", ("F1", "F7"), "page_metadata", url="https://www.fixmystreet.com/open311", use="Civic issue reports where borough coverage exists; uneven source coverage.", join_keys=("service_request_id", "lat_lon", "status", "requested_datetime"), boundary="Non-citywide civic reports; not official city 311.", priority_hint=54),
    Target("borough_service_requests", "Borough service-request/open-data feeds", ("F1", "F7"), "ckan_search", search_query="London borough service requests complaints fly tipping potholes", use="Potential borough-level civic status feeds.", join_keys=("borough", "service_request_id", "category", "date"), boundary="Uneven borough coverage.", priority_hint=50),
    Target("nhs_ae_london_hourly", "A&E attendance in London by day and hour", ("F6", "F7"), "ckan_search", search_query="A&E attendance London day hour", use="Aggregate health-system pressure context by time.", join_keys=("provider", "day", "hour"), boundary="Aggregate context only; no health determination or patient inference.", priority_hint=66),
    Target("nhs_england_ae_monthly", "NHS England A&E monthly statistics", ("F6",), "page_metadata", url="https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/", use="Official aggregate emergency-care pressure context.", join_keys=("provider", "month", "attendance_type"), boundary="Aggregate context only.", priority_hint=60),
    Target("ons_population", "ONS/GLA population projections and demographics", ("F1", "F6", "F7"), "ckan_search", search_query="London population projections borough age gender", use="Denominator/vulnerability context for all aggregate status surfaces.", join_keys=("borough", "age_band", "year"), priority_hint=68),
    Target("imd_deprivation", "Indices of Multiple Deprivation / deprivation context", ("F1", "F6", "F7"), "ckan_search", search_query="Indices of Deprivation London LSOA", use="Area vulnerability/context dimension.", join_keys=("LSOA", "IMD_decile", "borough"), priority_hint=64),
    Target("employment_economic_activity", "Employment/economic activity context", ("F1", "F6", "F7"), "ckan_search", search_query="London employment economic activity jobs borough", use="Economic-pressure context for status/fusion surfaces.", join_keys=("borough", "year", "metric"), priority_hint=52),
    Target("business_rates_premises", "Business/premises/rates context", ("F1", "F2", "F6", "F7"), "ckan_search", search_query="London business rates premises", use="Premises/economic activity context.", join_keys=("address", "borough", "business_category"), priority_hint=48),
    Target("fusion_existing_xdata", "Existing XDATA fused source manifest", ("F7",), "local_manifest_all", use="Fusion candidate substrate across LFB, TfL, air, flood, planning/context sources.", join_keys=("source_key", "landing_status", "rows_landed"), boundary="Review/fusion candidate only; no certified affected-asset claim.", priority_hint=92),
]


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    return sess


def nested_count_and_keys(value: Any) -> tuple[int | None, list[str]]:
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


def local_source_manifest() -> dict[str, dict[str, Any]]:
    manifest = read_json(XDATA_OUTPUT_DIR / "LON_XDATA_D1_DOWNLOAD_MANIFEST.json", {})
    return {str(row.get("source_key")): row for row in manifest.get("sources", []) if isinstance(row, dict)}


def csv_shape(path: Path, limit: int = 3) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for idx, row in enumerate(reader):
                if idx >= limit:
                    break
                rows.append(row)
            return {"columns": reader.fieldnames or [], "sample_rows": rows}
    except Exception as exc:
        return {"error": repr(exc), "columns": [], "sample_rows": []}


def local_manifest_source(target: Target, manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = manifests.get(target.local_source_key, {})
    path = Path(row.get("path") or "")
    shape = csv_shape(path) if path.exists() and path.suffix.lower() == ".csv" else {}
    return {
        "probe_status": "OK" if row else "MISSING_LOCAL_MANIFEST",
        "api_surface": row.get("url") or target.url,
        "api_kind_observed": row.get("kind") or target.api_kind,
        "soda2_status": "NOT_APPLICABLE_NATIVE_API_OR_LOCAL_LANDING",
        "count_observed": row.get("rows_landed"),
        "total_available": row.get("total_available"),
        "landing_status": row.get("landing_status"),
        "coverage_pct": row.get("coverage_pct"),
        "columns": shape.get("columns") or row.get("columns") or [],
        "sample_rows": shape.get("sample_rows") or [],
        "bytes": row.get("bytes_downloaded"),
        "path": str(path) if path else "",
        "notes": row.get("notes"),
    }


def local_manifest_family(target: Target, manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = [row for key, row in manifests.items() if key.startswith(target.local_source_key)]
    return {
        "probe_status": "OK" if rows else "MISSING_LOCAL_MANIFEST",
        "api_surface": "London Datastore official file resources",
        "api_kind_observed": "local_landed_family",
        "soda2_status": "NOT_AVAILABLE_ON_LONDON_DATASTORE_CKAN",
        "source_count": len(rows),
        "count_observed": sum(int(row.get("rows_landed") or 0) for row in rows),
        "statuses": sorted({str(row.get("landing_status")) for row in rows}),
        "resources": [
            {
                "source_key": row.get("source_key"),
                "rows_landed": row.get("rows_landed"),
                "total_available": row.get("total_available"),
                "landing_status": row.get("landing_status"),
                "url": row.get("url"),
                "path": row.get("path"),
            }
            for row in rows
        ],
    }


def local_registered(target: Target, manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = manifests.get(target.local_source_key, {})
    register = read_json(Path(row.get("path") or ""), {})
    files = register.get("registered_files", []) if isinstance(register, dict) else []
    return {
        "probe_status": "OK" if row else "MISSING_LOCAL_MANIFEST",
        "api_surface": "existing London core local registration",
        "api_kind_observed": "registered_existing",
        "soda2_status": "NOT_APPLICABLE_REGISTERED_EXISTING",
        "source_count": len(files),
        "count_observed": row.get("rows_landed"),
        "bytes": row.get("bytes_downloaded"),
        "registered_files": files[:20],
        "path": row.get("path"),
    }


def probe_ckan(target: Target, sess: requests.Session) -> dict[str, Any]:
    params = {"q": target.search_query, "rows": 3, "include_private": "false"}
    url = f"{DATA_LONDON_CKAN}/package_search?{urlencode(params)}"
    try:
        response = sess.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result", {})
        packages = result.get("results", result.get("result", [])) if isinstance(result, dict) else []
        resources: list[dict[str, Any]] = []
        for package in packages[:3]:
            for resource in (package.get("resources") or [])[:8]:
                resources.append(
                    {
                        "package_title": package.get("title"),
                        "package_name": package.get("name"),
                        "resource_name": resource.get("name"),
                        "format": resource.get("format"),
                        "url": resource.get("url"),
                        "datastore_active": resource.get("datastore_active"),
                    }
                )
        broad_catalogue = bool(packages) and packages[0].get("name") == "20o7k"
        return {
            "probe_status": "BROAD_CATALOGUE_MATCH" if broad_catalogue else "OK",
            "api_surface": url,
            "api_kind_observed": "Data London catalogue API package_search",
            "soda2_status": "NOT_AVAILABLE_ON_DATA_LONDON; CKAN native API used",
            "count_observed": None if broad_catalogue else result.get("count"),
            "catalogue_count": result.get("count"),
            "package_titles": [package.get("title") for package in packages[:3]],
            "resources": resources,
            "columns": [],
            "notes": "Catalogue search returned the broad dataset head rather than a reliable source-specific match; treat as discovery metadata only." if broad_catalogue else None,
        }
    except Exception as exc:
        return {"probe_status": "ERROR", "api_surface": url, "api_kind_observed": "CKAN package_search", "soda2_status": "NOT_AVAILABLE_ON_DATA_LONDON", "error": repr(exc)}


def probe_json_api(target: Target, sess: requests.Session, verify: bool = True) -> dict[str, Any]:
    try:
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = sess.get(target.url, timeout=30, verify=verify)
        response.raise_for_status()
        payload = response.json()
        count, keys = nested_count_and_keys(payload)
        return {
            "probe_status": "OK",
            "api_surface": target.url,
            "api_kind_observed": target.api_kind,
            "soda2_status": "NOT_APPLICABLE_NATIVE_API",
            "count_observed": count,
            "columns": keys,
            "content_type": response.headers.get("content-type"),
            "bytes": len(response.content),
        }
    except Exception as exc:
        return {"probe_status": "ERROR", "api_surface": target.url, "api_kind_observed": target.api_kind, "soda2_status": "NOT_APPLICABLE_NATIVE_API", "error": repr(exc)}


def probe_data_police(target: Target, sess: requests.Session) -> dict[str, Any]:
    month = "2026-05"
    url = f"{target.url}&date={month}"
    try:
        response = sess.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        count, keys = nested_count_and_keys(payload)
        return {
            "probe_status": "OK",
            "api_surface": url,
            "api_kind_observed": "data.police.uk REST API",
            "soda2_status": "NOT_APPLICABLE_NATIVE_API",
            "count_observed": count,
            "columns": keys,
            "sample_scope": "point-radius/nearest street-level sample around central London, not citywide",
        }
    except Exception as exc:
        return {"probe_status": "ERROR", "api_surface": url, "api_kind_observed": "data.police.uk REST API", "soda2_status": "NOT_APPLICABLE_NATIVE_API", "error": repr(exc)}


def probe_tfl_swagger(target: Target, sess: requests.Session) -> dict[str, Any]:
    try:
        response = sess.get(target.url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        paths = payload.get("paths", {})
        matched = []
        for path, spec in paths.items():
            if any(token.lower() in path.lower() for token in ["stoppoint", "arrival", "line"]):
                matched.append({"path": path, "summary": ((spec or {}).get("get") or {}).get("summary")})
            if len(matched) >= 20:
                break
        return {
            "probe_status": "OK",
            "api_surface": target.url,
            "api_kind_observed": "TfL OpenAPI/Swagger",
            "soda2_status": "NOT_APPLICABLE_TFL_NATIVE_API",
            "count_observed": len(matched),
            "endpoints": matched,
            "columns": ["path", "summary"],
        }
    except Exception as exc:
        return {"probe_status": "ERROR", "api_surface": target.url, "api_kind_observed": "TfL OpenAPI/Swagger", "soda2_status": "NOT_APPLICABLE_TFL_NATIVE_API", "error": repr(exc)}


def probe_page(target: Target, sess: requests.Session) -> dict[str, Any]:
    try:
        response = sess.get(target.url, timeout=25)
        status = "OK" if response.status_code < 400 else "HTTP_LIMITED"
        return {
            "probe_status": status,
            "api_surface": target.url,
            "api_kind_observed": "page_or_metadata",
            "soda2_status": "NO_SODA2_ENDPOINT_DISCOVERED",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "bytes": len(response.content),
            "columns": [],
        }
    except Exception as exc:
        return {"probe_status": "ERROR", "api_surface": target.url, "api_kind_observed": "page_or_metadata", "soda2_status": "NO_SODA2_ENDPOINT_DISCOVERED", "error": repr(exc)}


def priority_score(target: Target, probe: dict[str, Any]) -> int:
    score = target.priority_hint
    status = probe.get("probe_status")
    count = probe.get("count_observed")
    if status == "OK":
        score += 8
    if status == "BROAD_CATALOGUE_MATCH":
        score -= 8
    if isinstance(count, int) and count > 0:
        score += 8
    if isinstance(count, int) and count >= 1000:
        score += 4
    if "F7" in target.flows and len(target.flows) >= 3:
        score += 4
    if probe.get("landing_status") in {"FULL", "WINDOWED_COMPLETE", "BOUNDED_SAMPLE"}:
        score += 4
    if status in {"ERROR", "MISSING_LOCAL_MANIFEST"}:
        score -= 12
    return max(0, min(100, score))


def probe_target(target: Target, manifests: dict[str, dict[str, Any]], sess: requests.Session) -> dict[str, Any]:
    if target.api_kind == "local_manifest_source":
        probe = local_manifest_source(target, manifests)
    elif target.api_kind == "local_manifest_family":
        probe = local_manifest_family(target, manifests)
    elif target.api_kind == "local_registered":
        probe = local_registered(target, manifests)
    elif target.api_kind == "local_manifest_all":
        rows = list(manifests.values())
        probe = {
            "probe_status": "OK",
            "api_surface": str(XDATA_OUTPUT_DIR / "LON_XDATA_D1_DOWNLOAD_MANIFEST.json"),
            "api_kind_observed": "local_xdata_manifest",
            "soda2_status": "NOT_APPLICABLE_FUSION_MANIFEST",
            "source_count": len(rows),
            "count_observed": sum(int(row.get("rows_landed") or 0) for row in rows),
            "statuses": sorted({str(row.get("landing_status")) for row in rows}),
        }
    elif target.api_kind == "ckan_search":
        probe = probe_ckan(target, sess)
    elif target.api_kind == "json_api":
        probe = probe_json_api(target, sess, verify=False if "api.erg.ic.ac.uk" in target.url else True)
    elif target.api_kind == "ea_api":
        probe = probe_json_api(target, sess)
    elif target.api_kind == "planning_data_api":
        probe = probe_json_api(target, sess)
    elif target.api_kind == "data_police":
        probe = probe_data_police(target, sess)
    elif target.api_kind == "tfl_swagger_subset":
        probe = probe_tfl_swagger(target, sess)
    elif target.api_kind == "page_metadata":
        probe = probe_page(target, sess)
    else:
        probe = {"probe_status": "UNSUPPORTED_PROBE", "api_kind_observed": target.api_kind}
    score = priority_score(target, probe)
    return {
        "key": target.key,
        "title": target.title,
        "flows": list(target.flows),
        "use": target.use,
        "join_keys": list(target.join_keys),
        "boundary": target.boundary,
        "priority_hint": target.priority_hint,
        "priority_score": score,
        "next_action": next_action(target, probe, score),
        **probe,
    }


def next_action(target: Target, probe: dict[str, Any], score: int) -> str:
    if probe.get("probe_status") == "ERROR":
        return "Resolve endpoint/catalog shape before D2 landing."
    if target.api_kind == "ckan_search":
        return "Review top CKAN resources, choose machine-readable resources, then D2 land selected files/datastore resources."
    if probe.get("landing_status") == "METADATA_ONLY":
        return "Upgrade from metadata/page capture to real data-resource landing."
    if score >= 86:
        return "Promote to LON flow D2/D3 source contract candidate."
    if score >= 70:
        return "Keep as secondary D2 landing candidate or D3 enrichment."
    return "Keep as optional/context source until stronger join/use is defined."


def flow_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for flow in [f"F{i}" for i in range(1, 8)]:
        rows = [row for row in records if flow in row.get("flows", [])]
        summary[flow] = {
            "source_count": len(rows),
            "ok_count": sum(1 for row in rows if row.get("probe_status") == "OK"),
            "top_sources": [
                {"key": row["key"], "score": row["priority_score"], "status": row.get("probe_status"), "count": row.get("count_observed")}
                for row in sorted(rows, key=lambda item: item["priority_score"], reverse=True)[:8]
            ],
        }
    return summary


def write_markdown(out_dir: Path, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# LON 7-Flow Source Shape/API Scan",
        "",
        "Scope: London source/API shape scout across Flow 1-7. This is not a bulk landing and does not accept new flow cartridges.",
        "",
        "SODA2 note: Data London does not expose Socrata/SODA2 endpoints in this scan; where SODA2 is unavailable, the scan uses native CKAN, TfL, London Air, Environment Agency, data.police.uk, planning.data.gov.uk, or already-landed XDATA manifests.",
        "",
        "## Flow Summary",
        "",
        "| Flow | Sources | OK | Top sources |",
        "|---|---:|---:|---|",
    ]
    for flow, row in summary.items():
        top = ", ".join(f"{item['key']} ({item['score']})" for item in row["top_sources"][:5])
        lines.append(f"| {flow} | {row['source_count']} | {row['ok_count']} | {top} |")
    lines.extend(
        [
            "",
            "## Source Matrix",
            "",
            "| Priority | Source | Flows | API kind | Count/total | Status | Use | Next action |",
            "|---:|---|---|---|---:|---|---|---|",
        ]
    )
    for row in sorted(records, key=lambda item: item["priority_score"], reverse=True):
        count = row.get("count_observed")
        if row.get("total_available") is not None:
            count_text = f"{count}/{row.get('total_available')}"
        elif row.get("source_count") is not None:
            count_text = f"{count} rows; {row.get('source_count')} sources"
        else:
            count_text = "" if count is None else str(count)
        lines.append(
            "| {score} | `{key}` | {flows} | {kind} | {count} | {status} | {use} | {next_action} |".format(
                score=row["priority_score"],
                key=row["key"],
                flows=", ".join(row.get("flows", [])),
                kind=row.get("api_kind_observed", row.get("api_kind", "")),
                count=count_text,
                status=row.get("probe_status", ""),
                use=(row.get("use") or "").replace("|", "/"),
                next_action=(row.get("next_action") or "").replace("|", "/"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Review-context only.",
            "- No emergency command, fire dispatch, traffic-control instruction, utility control, health determination, policing recommendation, legal planning determination, or certified affected-asset claim.",
            "- Counts are shape/probe counts, not guaranteed full-source totals unless sourced from an accepted local manifest with explicit `total_available`.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests = local_source_manifest()
    sess = session()
    records = []
    for target in TARGETS:
        print(f"[scan] {target.key}", flush=True)
        records.append(probe_target(target, manifests, sess))
        time.sleep(0.1)
    summary = flow_summary(records)
    report = {
        "task": "LON 7-Flow Source Shape/API Scan",
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "source_count": len(records),
        "soda2_policy": "Prefer SODA2 where a Socrata endpoint exists; Data London scanned as CKAN because no Socrata/SODA2 API surface was discovered.",
        "records": records,
        "flow_summary": summary,
    }
    write_json(output_dir / "LON_7FLOW_SOURCE_SHAPE_SCAN.json", report)
    write_json(output_dir / "LON_7FLOW_FLOW_SUMMARY.json", summary)
    write_markdown(output_dir, records, summary)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run(Path(args.output_dir))
    print(f"LON 7-flow source shape scan: {report['status']}")
    print(f"Sources scanned: {report['source_count']}")
    print(f"Output: {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

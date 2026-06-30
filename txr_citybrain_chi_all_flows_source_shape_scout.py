from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


TASK = "CHI-ALLFLOWS-D1_SOURCE_SHAPE_SCOUT"
OUT_DIR = Path("outputs/chi_allflows_d1_source_shape_scout")
USER_AGENT = "TXR-CityBrain-CHI-AllFlows-Source-Shape-Scout/1.0"


FLOW_LABELS = {
    "F1": "Situational Status",
    "F2": "Planning / Compliance",
    "F3": "Incident / Affected Context",
    "F4": "Mobility / Crowd / Transport / Environment",
    "F5": "Flood / Climate / Asset Risk",
    "F6": "Industrial / Sequencing",
    "F7": "Civic + Sensor Fusion",
}


@dataclass
class Candidate:
    source_key: str
    name: str
    family: str
    domain: str | None = None
    dataset_id: str | None = None
    flows: list[str] = field(default_factory=list)
    reason: str = ""
    priority_hint: str = "medium"
    non_socrata_url: str | None = None
    requires_key: bool = False
    boundary: str = "review-context only; no operational recommendation or certification"


CURATED: list[Candidate] = [
    Candidate("311_service_requests", "311 Service Requests", "civic_service", "data.cityofchicago.org", "v6vf-nfxy", ["F1", "F5", "F7"], "Primary civic-service/event spine."),
    Candidate("crimes_2001_present", "Crimes - 2001 to Present", "public_safety", "data.cityofchicago.org", "ijzp-q8t2", ["F1", "F3"], "Block-level safety context only; do not use as operational policing recommendation."),
    Candidate("traffic_crashes_crashes", "Traffic Crashes - Crashes", "traffic_incident", "data.cityofchicago.org", "85ca-t3if", ["F1", "F3", "F4"], "Crash event table."),
    Candidate("traffic_crashes_vehicles", "Traffic Crashes - Vehicles", "traffic_incident", "data.cityofchicago.org", "68nd-jvt3", ["F3", "F4"], "Crash vehicle context linked to crash record id."),
    Candidate("traffic_crashes_people", "Traffic Crashes - People", "traffic_incident", "data.cityofchicago.org", "u6pd-qa9d", ["F3"], "Crash people context; privacy-safe use only."),
    Candidate("traffic_tracker_historical", "Traffic Tracker Historical 2024-Current", "mobility", "data.cityofchicago.org", "4g9f-3jbs", ["F1", "F3", "F4"], "Segment speed history."),
    Candidate("traffic_tracker_current", "Traffic Tracker - Current Congestion Estimates", "mobility", "data.cityofchicago.org", "n4j6-wkkf", ["F1", "F4"], "Current arterial segment speed context."),
    Candidate("arterial_daily_traffic", "Average Daily Traffic Counts", "mobility", "data.cityofchicago.org", "mi9s-c3e9", ["F1", "F4"], "Road demand baseline."),
    Candidate("divvy_trips", "Divvy Trips", "micromobility", "data.cityofchicago.org", "fg6s-gzvg", ["F1", "F4"], "Micromobility demand history."),
    Candidate("taxi_trips", "Taxi Trips", "mobility", "data.cityofchicago.org", "wrvz-psew", ["F1", "F4", "F6"], "Mobility demand and sequencing context."),
    Candidate("building_footprints", "Building Footprints", "base_geography", "data.cityofchicago.org", "syp8-uezg", ["F1", "F2", "F3", "F5", "F7"], "Building geometry/context."),
    Candidate("street_center_lines", "Street Center Lines", "base_geography", "data.cityofchicago.org", "6imu-meau", ["F1", "F3", "F4", "F6"], "Road graph/context backbone."),
    Candidate("building_permits", "Building Permits", "planning_compliance", "data.cityofchicago.org", "ydr8-5enu", ["F2", "F5", "F6"], "Permitting activity and construction context."),
    Candidate("building_violations", "Building Violations", "planning_compliance", "data.cityofchicago.org", "22u3-xenr", ["F2", "F5"], "Compliance context."),
    Candidate("business_licenses", "Business Licenses", "business", "data.cityofchicago.org", "r5kz-chrr", ["F1", "F2", "F6"], "Commercial activity context."),
    Candidate("active_business_licenses", "Active Business Licenses", "business", "data.cityofchicago.org", "uupf-x98q", ["F1", "F2", "F6"], "Current business/licensing context."),
    Candidate("food_inspections", "Food Inspections", "business_health", "data.cityofchicago.org", "4ijn-s7e5", ["F1", "F2", "F7"], "Inspection context; no health determination."),
    Candidate("speed_camera_violations", "Speed Camera Violations", "traffic_enforcement_context", "data.cityofchicago.org", "hhkd-xvj4", ["F1", "F3", "F4"], "Aggregate traffic-risk context only."),
    Candidate("red_light_camera_violations", "Red Light Camera Violations", "traffic_enforcement_context", "data.cityofchicago.org", "cjjf-sxex", ["F1", "F3", "F4"], "Aggregate traffic-risk context only."),
    Candidate("open_air_individual", "Open Air Chicago Individual Measurements", "environment", "data.cityofchicago.org", "xfya-dxtq", ["F4", "F5", "F7"], "Environmental observations; no health determination."),
    Candidate("open_air_hourly", "Open Air Chicago Hour Aggregations", "environment", "data.cityofchicago.org", "di9s-96ws", ["F4", "F5", "F7"], "Hourly environmental observations; no health determination."),
    Candidate("array_of_things_locations", "Array of Things Locations", "sensor", "data.cityofchicago.org", "6rq2-yx28", ["F4", "F5", "F7"], "Sensor node location context."),
    Candidate("beach_water_sensors", "Beach Water Sensors", "sensor", "data.cityofchicago.org", "qmqz-2xku", ["F5", "F7"], "Water/environment sensor context."),
    Candidate("green_infra_sensors", "Smart Green Infrastructure Monitoring Sensors", "sensor_climate", "data.cityofchicago.org", "ggws-77ih", ["F5", "F7"], "Stormwater/green-infra monitoring context."),
    Candidate("environmental_storage_tanks", "CDPH Environmental Storage Tanks", "environment_risk", "data.cityofchicago.org", "ug5u-hxnx", ["F5", "F6"], "Environmental asset/risk context."),
    Candidate("air_records", "AIR", "environment_risk", "data.cityofchicago.org", "sdqv-eu26", ["F5", "F6"], "Air/environmental record context; no health determination."),
    Candidate("fire_stations", "Fire Stations", "facilities", "data.cityofchicago.org", "28km-gtjn", ["F1", "F3", "F7"], "Response-resource context only."),
    Candidate("police_stations", "Police Stations", "facilities", "data.cityofchicago.org", "z8bn-74gv", ["F1", "F3", "F7"], "Public-safety facility context only."),
    Candidate("hospitals", "Hospitals", "facilities", "data.cityofchicago.org", "mkjv-t4kt", ["F1", "F3", "F7"], "Civic facility/resource context only."),
    Candidate("libraries", "Libraries", "facilities", "data.cityofchicago.org", "x8fc-8rcq", ["F1", "F7"], "Civic facility context."),
    Candidate("schools", "Schools", "facilities", "data.cityofchicago.org", "mv87-m4mi", ["F1", "F5", "F7"], "Civic facility context."),
    Candidate("wards", "Wards", "boundary", "data.cityofchicago.org", "p293-wvbd", ["F1", "F2", "F5", "F7"], "Aggregation geography."),
    Candidate("community_areas", "Community Areas", "boundary", "data.cityofchicago.org", "igwz-8jzy", ["F1", "F2", "F5", "F7"], "Aggregation geography."),
    Candidate("police_districts", "Police Districts", "boundary", "data.cityofchicago.org", "fthy-xz3r", ["F1", "F3", "F7"], "Aggregation geography."),
    Candidate("cook_parcels_chicago", "Cook County Parcel Universe - Chicago Filter", "parcel", "datacatalog.cookcountyil.gov", "nj4t-kc8j", ["F2", "F5", "F7"], "Parcel/PIN identity anchor; filter to CITY OF CHICAGO.", priority_hint="high"),
    Candidate("cook_parcel_sales", "Cook County Assessor Parcel Sales", "parcel_market", "datacatalog.cookcountyil.gov", "wvhk-k5uv", ["F2", "F5"], "Parcel market/transaction context."),
    Candidate("zoning_current_boundaries", "Boundaries - Zoning Districts (current)", "planning_zoning", "data.cityofchicago.org", "dj47-wfun", ["F2", "F5", "F6"], "Zoning geography for planning/compliance and land-use context."),
    Candidate("zoning_tabular", "Zoning", "planning_zoning", "data.cityofchicago.org", "nifi-zqag", ["F2", "F5", "F6"], "Zoning district/tabular context for parcel/building analysis."),
    Candidate("pedestrian_streets", "Zoning Pedestrian Streets", "planning_mobility", "data.cityofchicago.org", "v6kn-gc9b", ["F2", "F4", "F6"], "Pedestrian-street zoning and corridor context."),
    Candidate("transportation_department_permits", "Transportation Department Permits", "street_work", "data.cityofchicago.org", "pubx-yq2d", ["F2", "F4", "F6"], "Street-work/transportation permit context for sequencing."),
    Candidate("roadway_construction_moratoriums", "Roadway Construction Moratoriums", "street_work", "data.cityofchicago.org", "ndbz-vy4e", ["F4", "F6"], "Roadway construction constraint context."),
    Candidate("height_weight_limits", "Height and Weight Limits for Trucks and Large Vehicles", "freight_logistics", "data.cityofchicago.org", "nc38-56x2", ["F4", "F6"], "Truck/large-vehicle network constraint context."),
    Candidate("tnp_trips_2025", "Transportation Network Providers - Trips (2025-)", "mobility_tnp", "data.cityofchicago.org", "6dvr-xwnh", ["F1", "F4", "F6"], "Current TNP trip demand context."),
    Candidate("tnp_trips_2023_2024", "Transportation Network Providers - Trips (2023-2024)", "mobility_tnp", "data.cityofchicago.org", "n26f-ihde", ["F1", "F4", "F6"], "Recent TNP trip demand context."),
    Candidate("tnp_trips_2018_2022", "Transportation Network Providers - Trips (2018-2022)", "mobility_tnp", "data.cityofchicago.org", "m6dm-c72p", ["F1", "F4", "F6"], "Historical TNP trip demand context."),
    Candidate("tnp_vehicles", "Transportation Network Providers - Vehicles", "mobility_tnp", "data.cityofchicago.org", "bc6b-sq4u", ["F4", "F6"], "TNP vehicle/inspection context."),
    Candidate("special_events", "Special Events", "events", "data.cityofchicago.org", "xgse-8eg7", ["F1", "F4", "F6", "F7"], "Public event context for mobility/civic status."),
    Candidate("library_events", "Chicago Public Library Events", "events", "data.cityofchicago.org", "vsdy-d8k7", ["F1", "F7"], "Civic event context."),
    Candidate("utility_hit_tickets", "811 Chicago Utility Hit Tickets", "utility_context", "data.cityofchicago.org", "nphj-5zur", ["F3", "F5", "F6"], "Utility-hit incident/context only; no utility-control recommendation."),
    Candidate("open_air_day", "Open Air Chicago Day Aggregations", "environment", "data.cityofchicago.org", "rtmx-vkjr", ["F4", "F5", "F7"], "Daily environmental aggregation; no health determination."),
    Candidate("beach_sensor_locations", "Beach Water and Weather Sensor Locations", "sensor", "data.cityofchicago.org", "g3ip-u8rb", ["F5", "F7"], "Beach sensor location context."),
    Candidate("beach_weather_stations", "Beach Weather Stations - Automated Sensors", "sensor", "data.cityofchicago.org", "k7hf-8y75", ["F5", "F7"], "Beach weather observations; no safety/health determination."),
    Candidate("energy_benchmarking_current", "Chicago Energy Benchmarking - Covered Buildings", "asset_climate", "data.cityofchicago.org", "g5i5-yz37", ["F2", "F5"], "Building energy/climate context."),
    Candidate("energy_benchmarking_history", "Chicago Energy Benchmarking", "asset_climate", "data.cityofchicago.org", "xq83-jr8c", ["F2", "F5"], "Building energy/climate history."),
    Candidate("cdph_environmental_permits", "CDPH Environmental Permits", "environment_compliance", "data.cityofchicago.org", "ir7v-8mc8", ["F2", "F5", "F6"], "Environmental permit/compliance context."),
    Candidate("cdph_environmental_inspections", "CDPH Environmental Inspections", "environment_compliance", "data.cityofchicago.org", "i9rk-duva", ["F2", "F5", "F6"], "Environmental inspection context."),
    Candidate("cdph_environmental_complaints", "CDPH Environmental Complaints", "environment_compliance", "data.cityofchicago.org", "fypr-ksnz", ["F1", "F5", "F7"], "Environmental complaint/civic context."),
    Candidate("cdph_environmental_enforcement", "CDPH Environmental Enforcement", "environment_compliance", "data.cityofchicago.org", "yqn4-3th2", ["F2", "F5", "F6"], "Environmental enforcement context only; no enforcement recommendation."),
    Candidate("cdph_asbestos_demolition", "CDPH Environmental Asbestos and Demolition Notification", "environment_compliance", "data.cityofchicago.org", "qhb4-qx8k", ["F2", "F5", "F6"], "Asbestos/demolition notification context."),
    Candidate("environmental_hold_lust_nfr", "CDPH Environmental Hold on City-Issued Permits and LUST NFR", "environment_compliance", "data.cityofchicago.org", "6gqn-e2ij", ["F2", "F5", "F6"], "Environmental hold/LUST context for permits."),
    Candidate("cta_gtfs_static", "CTA GTFS static ZIP", "transit", None, None, ["F1", "F3", "F4"], "Static transit topology/schedule; not live status.", non_socrata_url="https://www.transitchicago.com/downloads/sch_data/google_transit.zip"),
    Candidate("cta_train_tracker", "CTA Train Tracker API", "transit_live", None, None, ["F1", "F3", "F4"], "Live train arrivals; developer key required.", non_socrata_url="https://www.transitchicago.com/developers/traintracker/", requires_key=True),
    Candidate("cta_bus_tracker", "CTA Bus Tracker API", "transit_live", None, None, ["F1", "F3", "F4"], "Live bus predictions/vehicles; developer key required.", non_socrata_url="https://www.transitchicago.com/developers/bustracker/", requires_key=True),
    Candidate("cta_customer_alerts", "CTA Customer Alerts API", "transit_live", None, None, ["F1", "F3", "F4"], "Transit disruption alert context; key/rules to verify.", non_socrata_url="https://www.transitchicago.com/developers/alerts/", requires_key=True),
]


CATALOG_SEARCHES = {
    "F1": ["service requests", "traffic tracker", "crimes", "traffic crashes", "business licenses", "facilities"],
    "F2": ["zoning", "land use", "building permits", "building violations", "inspections", "licenses", "parcels"],
    "F3": ["traffic crashes", "fire", "police", "emergency", "road disruptions", "traffic"],
    "F4": ["CTA", "Divvy", "taxi trips", "transportation network provider", "traffic", "street closures"],
    "F5": ["flood", "water", "sewer", "green infrastructure", "environment", "climate", "storm"],
    "F6": ["construction", "street closures", "permits", "airport", "freight", "industrial", "environmental storage tanks"],
    "F7": ["311", "sensor", "array of things", "open air", "beach", "facilities", "library", "schools"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def get_json(session: requests.Session, url: str, params: dict[str, Any] | None = None, timeout: int = 45) -> tuple[int | None, Any, str | None]:
    try:
        response = session.get(url, params=params, timeout=timeout)
        status = response.status_code
        if status >= 400:
            return status, None, response.text[:500]
        return status, response.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, None, repr(exc)


def count_socrata(session: requests.Session, domain: str, dataset_id: str, where: str | None = None) -> tuple[int | None, str | None]:
    params: dict[str, str] = {"$select": "count(*)"}
    if where:
        params["$where"] = where
    status, payload, error = get_json(session, f"https://{domain}/resource/{dataset_id}.json", params=params, timeout=90)
    if error:
        return None, f"{status}: {error}"
    try:
        row = payload[0] if isinstance(payload, list) and payload else {}
        value = row.get("count") or row.get("count_1") or next(iter(row.values()))
        return int(value), None
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def sample_socrata(session: requests.Session, domain: str, dataset_id: str, where: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    params: dict[str, str] = {"$limit": "3"}
    if where:
        params["$where"] = where
    status, payload, error = get_json(session, f"https://{domain}/resource/{dataset_id}.json", params=params, timeout=45)
    if error:
        return [], f"{status}: {error}"
    return payload if isinstance(payload, list) else [], None


def infer_fields(columns: list[dict[str, Any]], sample: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(col.get("fieldName") or col.get("name") or "") for col in columns if col.get("fieldName") or col.get("name")]
    types = {str(col.get("fieldName") or col.get("name")): col.get("dataTypeName") for col in columns if col.get("fieldName") or col.get("name")}
    lower = {name: name.lower() for name in names}
    date_fields = [name for name, low in lower.items() if "date" in low or "time" in low or types.get(name) in {"calendar_date", "floating_timestamp", "fixed_timestamp"}]
    geo_fields = [name for name, low in lower.items() if "latitude" in low or "longitude" in low or "location" in low or types.get(name) in {"point", "multipolygon", "line", "location"}]
    id_fields = [name for name, low in lower.items() if low in {"id", "objectid", "pin", "sr_number", "request_number", "crash_record_id"} or low.endswith("_id") or "number" in low]
    sample_keys = sorted({key for row in sample for key in row.keys()})[:40]
    return {
        "column_count": len(names),
        "columns": names[:80],
        "date_time_fields": date_fields[:20],
        "geo_fields": geo_fields[:20],
        "id_join_key_candidates": id_fields[:25],
        "sample_keys": sample_keys,
    }


def priority_score(candidate: Candidate, count: int | None, field_info: dict[str, Any], api_ok: bool) -> tuple[int, str]:
    score = 0
    if candidate.priority_hint == "high":
        score += 2
    if api_ok:
        score += 2
    if count is not None:
        if count > 1_000_000:
            score += 2
        elif count > 10_000:
            score += 1
    if field_info.get("date_time_fields"):
        score += 1
    if field_info.get("geo_fields"):
        score += 1
    if field_info.get("id_join_key_candidates"):
        score += 1
    if len(candidate.flows) >= 3:
        score += 1
    if candidate.requires_key:
        score -= 2
    if score >= 8:
        return score, "P0"
    if score >= 6:
        return score, "P1"
    if score >= 4:
        return score, "P2"
    return score, "P3"


def catalog_discover(session: requests.Session) -> tuple[list[Candidate], list[dict[str, Any]]]:
    discovered: dict[tuple[str, str], Candidate] = {}
    search_log: list[dict[str, Any]] = []
    for flow, terms in CATALOG_SEARCHES.items():
        for term in terms:
            params = {
                "domains": "data.cityofchicago.org,datacatalog.cookcountyil.gov",
                "search": term,
                "limit": 12,
                "only": "datasets",
            }
            status, payload, error = get_json(session, "https://api.us.socrata.com/api/catalog/v1", params=params, timeout=45)
            results = payload.get("results", []) if isinstance(payload, dict) else []
            search_log.append({"flow": flow, "term": term, "status": status, "result_count": len(results), "error": error})
            for result in results:
                resource = result.get("resource", {})
                metadata = result.get("metadata", {})
                domain = metadata.get("domain") or resource.get("domain")
                dataset_id = resource.get("id")
                name = resource.get("name") or metadata.get("name") or dataset_id
                if not domain or not dataset_id:
                    continue
                key = (domain, dataset_id)
                candidate = discovered.get(key)
                if candidate is None:
                    candidate = Candidate(
                        source_key=f"catalog_{safe_key(domain)}_{dataset_id}",
                        name=name,
                        family="catalog_discovered",
                        domain=domain,
                        dataset_id=dataset_id,
                        flows=[flow],
                        reason=f"Catalog search hit for '{term}'.",
                        priority_hint="medium",
                    )
                    discovered[key] = candidate
                elif flow not in candidate.flows:
                    candidate.flows.append(flow)
    return list(discovered.values()), search_log


def source_record(session: requests.Session, candidate: Candidate) -> dict[str, Any]:
    if not candidate.domain or not candidate.dataset_id:
        return {
            "source_key": candidate.source_key,
            "name": candidate.name,
            "family": candidate.family,
            "flows": candidate.flows,
            "flow_labels": [FLOW_LABELS[flow] for flow in candidate.flows],
            "api_type": "non_socrata",
            "api_url": candidate.non_socrata_url,
            "soda2_url": None,
            "requires_key": candidate.requires_key,
            "total_available": None,
            "shape_status": "REFERENCE_ONLY",
            "reason": candidate.reason,
            "boundary": candidate.boundary,
            "priority_score": -1 if candidate.requires_key else 1,
            "priority_band": "KEY_BLOCKED" if candidate.requires_key else "P3",
        }

    view_url = f"https://{candidate.domain}/api/views/{candidate.dataset_id}.json"
    status, metadata, metadata_error = get_json(session, view_url, timeout=45)
    columns = metadata.get("columns", []) if isinstance(metadata, dict) else []
    where = "cook_municipality_name='CITY OF CHICAGO'" if candidate.source_key == "cook_parcels_chicago" else None
    count, count_error = count_socrata(session, candidate.domain, candidate.dataset_id, where=where)
    sample, sample_error = sample_socrata(session, candidate.domain, candidate.dataset_id, where=where)
    field_info = infer_fields(columns, sample)
    api_ok = status == 200 and metadata_error is None
    score, band = priority_score(candidate, count, field_info, api_ok)
    api_params = {"$limit": 50000}
    if where:
        api_params["$where"] = where
    soda2_url = f"https://{candidate.domain}/resource/{candidate.dataset_id}.json?{urlencode(api_params)}"
    record = {
        "source_key": candidate.source_key,
        "name": metadata.get("name", candidate.name) if isinstance(metadata, dict) else candidate.name,
        "family": candidate.family,
        "domain": candidate.domain,
        "dataset_id": candidate.dataset_id,
        "flows": sorted(candidate.flows),
        "flow_labels": [FLOW_LABELS[flow] for flow in sorted(candidate.flows)],
        "api_type": "socrata_soda2",
        "api_url": f"https://{candidate.domain}/resource/{candidate.dataset_id}.json",
        "soda2_url": soda2_url,
        "view_metadata_url": view_url,
        "human_url": f"https://{candidate.domain}/d/{candidate.dataset_id}",
        "requires_key": False,
        "total_available": count,
        "count_error": count_error,
        "metadata_status": status,
        "metadata_error": metadata_error,
        "sample_error": sample_error,
        "shape_status": "COUNTED_AND_SAMPLED" if count is not None and sample_error is None else "METADATA_ONLY_OR_PARTIAL",
        "field_info": field_info,
        "sample_rows": sample[:2],
        "updated_at": metadata.get("rowsUpdatedAt") if isinstance(metadata, dict) else None,
        "category": metadata.get("category") if isinstance(metadata, dict) else None,
        "attribution": metadata.get("attribution") if isinstance(metadata, dict) else None,
        "reason": candidate.reason,
        "boundary": candidate.boundary,
        "priority_score": score,
        "priority_band": band,
    }
    return record


def merge_candidates(curated: list[Candidate], discovered: list[Candidate]) -> list[Candidate]:
    merged: dict[tuple[str | None, str | None, str], Candidate] = {}
    for candidate in curated + discovered:
        key = (candidate.domain, candidate.dataset_id, candidate.non_socrata_url or "")
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue
        for flow in candidate.flows:
            if flow not in existing.flows:
                existing.flows.append(flow)
        if not existing.reason:
            existing.reason = candidate.reason
    return list(merged.values())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def render_markdown(records: list[dict[str, Any]], search_log: list[dict[str, Any]]) -> str:
    lines = [
        "# CHI-ALLFLOWS-D1 Source Shape Scout",
        "",
        f"Generated: `{utc_now()}`",
        "",
        "Scope: official Chicago/Cook/CTA sources across Flow 1-7. This pass probes metadata, counts, columns, and tiny samples; it does not bulk-download rows.",
        "",
        "SODA2 rule: Socrata datasets use `/resource/{dataset_id}.json` with `$limit=50000`; counts use `$select=count(*)`.",
        "",
        "Boundary: no emergency dispatch, no health determination, no enforcement recommendation, no certified affected-building/asset claim.",
        "",
        "## Priority Summary",
        "",
    ]
    for band in ["P0", "P1", "P2", "P3", "KEY_BLOCKED"]:
        subset = [row for row in records if row.get("priority_band") == band]
        lines.append(f"- `{band}`: {len(subset)} sources")
    lines.extend(["", "## Flow Coverage", ""])
    for flow, label in FLOW_LABELS.items():
        subset = [row for row in records if flow in row.get("flows", [])]
        counted = sum(1 for row in subset if row.get("total_available") is not None)
        rows = sum(int(row.get("total_available") or 0) for row in subset)
        lines.append(f"- `{flow}` {label}: {len(subset)} candidate sources, {counted} counted, {rows:,} combined counted rows/events")
    lines.extend(["", "## Highest-Priority Sources", ""])
    top = sorted(records, key=lambda row: (row.get("priority_score", -99), row.get("total_available") or 0), reverse=True)[:35]
    lines.append("| Priority | Source | Flows | Rows | API | Shape | Key fields | Use |")
    lines.append("|---|---|---|---:|---|---|---|---|")
    for row in top:
        fields = row.get("field_info", {})
        key_bits = ", ".join((fields.get("id_join_key_candidates") or fields.get("date_time_fields") or fields.get("geo_fields") or [])[:5])
        api = row.get("soda2_url") or row.get("api_url") or ""
        lines.append(
            f"| {row.get('priority_band')} | {row.get('name')} | {', '.join(row.get('flows', []))} | "
            f"{row.get('total_available') if row.get('total_available') is not None else ''} | {api} | "
            f"{row.get('shape_status')} | {key_bits} | {row.get('reason', '')} |"
        )
    lines.extend(["", "## Next Actions", ""])
    lines.extend(
        [
            "- Land only missing P0/P1 shape-critical sources first; avoid bulk until each join key and privacy boundary is clear.",
            "- Flow 2 should harden PIN/building/permit/violation/license joins before compliance cascade claims.",
            "- Flow 4 should add CTA live only after keys are available; GTFS remains static schedule context.",
            "- Flow 5 should prioritize 311 water/sewer/flood slices, green-infra sensors, buildings, parcels, and roads.",
            "- Flow 6 should stay framed as construction/street-work/logistics sequencing, not industrial control.",
        ]
    )
    lines.extend(["", "## Catalog Search Log", ""])
    for item in search_log:
        lines.append(f"- `{item['flow']}` search `{item['term']}`: {item['result_count']} results, status={item['status']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    discovered, search_log = catalog_discover(session)
    candidates = merge_candidates(CURATED, discovered)
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        print(f"[{index}/{len(candidates)}] {candidate.name} ({candidate.domain or 'non-socrata'} {candidate.dataset_id or ''})", flush=True)
        records.append(source_record(session, candidate))
        time.sleep(0.05)
    records = sorted(records, key=lambda row: (row.get("priority_band", "ZZ"), row.get("name", "")))
    by_flow = {
        flow: sorted([row for row in records if flow in row.get("flows", [])], key=lambda row: (row.get("priority_band", "ZZ"), row.get("name", "")))
        for flow in FLOW_LABELS
    }
    report = {
        "task": TASK,
        "generated_at": utc_now(),
        "status": "PASS_WITH_SOURCE_LIMITATIONS",
        "scope": "metadata/count/sample source-shape scout only; no bulk download",
        "canonical_api_pattern": "https://{domain}/resource/{dataset_id}.json?$limit=50000",
        "source_count": len(records),
        "catalog_search_log": search_log,
        "records": records,
        "by_flow": by_flow,
        "boundaries": [
            "No emergency dispatch.",
            "No health determination from environmental data.",
            "No enforcement recommendation.",
            "No certified affected-building or affected-asset claim.",
            "CTA live APIs remain key/rule gated.",
        ],
    }
    write_json(OUT_DIR / "CHI_ALLFLOWS_D1_SOURCE_SHAPE_SCOUT.json", report)
    write_json(OUT_DIR / "CHI_ALLFLOWS_D1_BY_FLOW.json", by_flow)
    (OUT_DIR / "README.md").write_text(render_markdown(records, search_log), encoding="utf-8")
    print(f"Wrote {OUT_DIR.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

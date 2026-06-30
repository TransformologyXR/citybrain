#!/usr/bin/env python3
"""NYC source-shape scan for TXR City Brain flow planning.

This is a metadata/count pass only. It does not bulk-download data rows.
Socrata sources use the SODA2 `/resource/{dataset_id}.json` endpoint because
that is the target landing API for higher-limit pulls.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


USER_AGENT = "TXR-CityBrain-NYC-Source-Shape-Scan/1.0"
OUT_DIR = Path("outputs/nyc_flow_source_scan")


@dataclass(frozen=True)
class Candidate:
    key: str
    name: str
    flows: tuple[int, ...]
    priority: str
    source_type: str
    domain: str = ""
    dataset_id: str = ""
    url: str = ""
    use: str = ""
    notes: str = ""
    boundary: str = "review-context only; no operational command"


SOURCES: list[Candidate] = [
    Candidate("nyc_311_2020_present", "311 Service Requests from 2020 to Present", (1, 3, 4, 7), "P0", "socrata", "data.cityofnewyork.us", "erm2-nwe9", use="citywide civic condition stream; issue clustering; service context"),
    Candidate("nyc_311_2010_2019", "311 Service Requests from 2010 to 2019", (1, 7), "P2", "socrata", "data.cityofnewyork.us", "76ig-c548", use="historical baselines once current 311 is normalized"),
    Candidate("nyc_dob_now_build_filings", "DOB NOW Build Job Application Filings", (2, 3), "P0", "socrata", "data.cityofnewyork.us", "w9ak-ipjd", use="construction/compliance activity spine"),
    Candidate("nyc_dob_permit_issuance", "DOB Permit Issuance", (2, 3), "P0", "socrata", "data.cityofnewyork.us", "ipu4-2q9a", use="permit lifecycle and location/building context"),
    Candidate("nyc_dob_complaints", "DOB Complaints Received", (2, 3, 7), "P0", "socrata", "data.cityofnewyork.us", "eabe-havv", use="building complaint evidence and affected-context candidate signals"),
    Candidate("nyc_dob_violations", "DOB Violations", (2, 3), "P0", "socrata", "data.cityofnewyork.us", "3h2n-5cm9", use="compliance status and enforcement-history context"),
    Candidate("nyc_dob_ecb_violations", "DOB ECB Violations", (2, 3), "P1", "socrata", "data.cityofnewyork.us", "6bgk-3dad", use="ECB/OATH-linked compliance context"),
    Candidate("nyc_dob_safety_violations", "DOB Safety Violations", (2, 3), "P1", "socrata", "data.cityofnewyork.us", "855j-jady", use="safety-violation context; operator review only"),
    Candidate("nyc_hpd_hmc_complaints", "Housing Maintenance Code Complaints and Problems", (2, 3, 7), "P1", "socrata", "data.cityofnewyork.us", "ygpa-z7cr", use="housing condition evidence; complement to DOB"),
    Candidate("nyc_hpd_jurisdiction_buildings", "Buildings Subject to HPD Jurisdiction", (2, 3, 5, 7), "P1", "socrata", "data.cityofnewyork.us", "kj4p-ruqc", use="building universe for housing-context joins"),
    Candidate("nyc_pluto", "Primary Land Use Tax Lot Output / PLUTO", (2, 3, 5, 7), "P0", "socrata", "data.cityofnewyork.us", "64uk-42ks", use="parcel/tax-lot join spine for buildings, land use, zoning, risk"),
    Candidate("nyc_3d_building_model", "3-D Building Model", (2, 3, 5, 7), "P2", "socrata", "data.cityofnewyork.us", "tnru-abg2", use="3D geometry context; heavy asset, not first landing"),
    Candidate("nyc_1ft_dem", "1-foot Digital Elevation Model", (5,), "P2", "socrata", "data.cityofnewyork.us", "dpc8-z3jc", use="elevation/flood modeling; likely tile/file strategy"),
    Candidate("nyc_dot_traffic_speeds", "DOT Traffic Speeds", (1, 4, 7), "P0", "socrata", "data.cityofnewyork.us", "i4gi-tjb9", use="traffic state, congestion replay, mobility context"),
    Candidate("nyc_traffic_volume_counts", "Traffic Volume Counts Historical", (4, 7), "P0", "socrata", "data.cityofnewyork.us", "btm5-ppia", use="road demand baselines and calibration"),
    Candidate("nyc_street_closures_block", "Street Closures due to Construction Activities by Block", (2, 4), "P0", "socrata", "data.cityofnewyork.us", "i6b5-j7bu", use="construction mobility impact context"),
    Candidate("nyc_street_closures_intersection", "Street Closures due to Construction Activities by Intersection", (2, 4), "P1", "socrata", "data.cityofnewyork.us", "478a-yykk", use="intersection-level closure context"),
    Candidate("nyc_street_closures_combined", "Street Closures due to Construction Activities by Block and Intersection", (2, 4), "P1", "socrata", "data.cityofnewyork.us", "ezy6-djsf", use="combined closure context; de-duplicate with block/intersection feeds"),
    Candidate("nyc_mvc_crashes", "Motor Vehicle Collisions - Crashes", (1, 3, 4, 7), "P0", "socrata", "data.cityofnewyork.us", "h9gi-nx95", use="incident/mobility safety context"),
    Candidate("nyc_mvc_vehicles", "Motor Vehicle Collisions - Vehicles", (3, 4, 7), "P1", "socrata", "data.cityofnewyork.us", "bm4k-52h4", use="vehicle-level crash context"),
    Candidate("nyc_mvc_persons", "Motor Vehicle Collisions - Persons", (3, 4, 7), "P1", "socrata", "data.cityofnewyork.us", "f55k-p6yu", use="privacy-safe selected fields only for person context"),
    Candidate("nyc_ems_dispatch", "EMS Incident Dispatch Data", (1, 3, 4, 7), "P2", "socrata", "data.cityofnewyork.us", "76xm-jjuj", use="response-time modeling and public-safety context; high boundary risk", boundary="aggregate/replay only; no dispatch recommendation"),
    Candidate("nyc_fire_dispatch", "Fire Incident Dispatch Data", (1, 3, 4, 7), "P2", "socrata", "data.cityofnewyork.us", "8m42-w767", use="fire response modeling and context; high boundary risk", boundary="aggregate/replay only; no fire response instruction"),
    Candidate("nyc_air_quality", "Air Quality and Health Impacts", (1, 4, 5, 7), "P0", "socrata", "data.cityofnewyork.us", "c3uy-2p5r", use="environmental condition and long-run exposure context"),
    Candidate("nyc_queens_air_sensor_pilot", "Queens Air Quality Sensor Pilot", (1, 4, 7), "P2", "socrata", "data.cityofnewyork.us", "2juy-aj8e", use="sensor-pilot enrichment if coverage/window fits"),
    Candidate("nyc_flood_vulnerability_index", "NYC Flood Vulnerability Index", (5, 7), "P0", "socrata", "data.cityofnewyork.us", "mrjc-v9pm", use="flood/climate vulnerability screening"),
    Candidate("nyc_flood_vulnerability_index_map", "NYC Flood Vulnerability Index Map", (5, 7), "P0", "socrata", "data.cityofnewyork.us", "4vym-qrg3", use="FVI geography/map joins"),
    Candidate("nyc_ll84_energy_water", "NYC Building Energy and Water Disclosure LL84", (5, 7), "P0", "socrata", "data.cityofnewyork.us", "5zyy-y8am", use="building energy/water benchmark risk context"),
    Candidate("nyc_harbor_water_quality", "Harbor Water Quality", (5, 7), "P1", "socrata", "data.cityofnewyork.us", "5uug-f49n", use="water/environment context; station/time-series joins"),
    Candidate("nyc_facilities_database", "Facilities Database", (1, 3, 5, 7), "P0", "socrata", "data.cityofnewyork.us", "ji82-xba5", use="public/private facility context and proximity joins"),
    Candidate("nyc_parks_properties", "Parks Properties", (1, 5, 7), "P1", "socrata", "data.cityofnewyork.us", "enfh-gkve", use="park/open-space/facility context"),
    Candidate("nyc_school_points_2019_2020", "2019-2020 School Point Locations", (1, 3, 7), "P2", "socrata", "data.cityofnewyork.us", "a3nt-yts4", use="school/facility context; find newer source before priority landing"),
    Candidate("nyc_centerline", "Centerline", (2, 4, 7), "P1", "socrata", "data.cityofnewyork.us", "inkn-q76z", use="street network/geocoder support; not routing command"),
    Candidate("nyc_bike_routes", "New York City Bike Routes", (4, 7), "P1", "socrata", "data.cityofnewyork.us", "mzxg-pwib", use="bike mobility network context"),
    Candidate("nyc_taxi_zones", "NYC Taxi Zones", (4, 6, 7), "P1", "socrata", "data.cityofnewyork.us", "8meu-9t5y", use="zone geography for TLC/FHV aggregation"),
    Candidate("nyc_taxi_pickups_dropoffs_zone_industry", "Pickups and Drop-offs by Taxi Zone and Industry", (4, 6, 7), "P1", "socrata", "data.cityofnewyork.us", "c5iv-bn4s", use="mobility demand by taxi zone/industry"),
    Candidate("nyc_fhv_base_aggregate", "FHV Base Aggregate Report", (4, 6, 7), "P2", "socrata", "data.cityofnewyork.us", "2v9c-2k7f", use="FHV operating context; aggregate only"),
    Candidate("nyc_permitted_events", "NYC Permitted Event Information", (1, 4, 7), "P1", "socrata", "data.cityofnewyork.us", "tvpp-9vvx", use="event/crowd/mobility context"),
    Candidate("nyc_restaurant_inspections", "DOHMH Restaurant Inspection Results", (1, 7), "P3", "socrata", "data.cityofnewyork.us", "43nn-pn8j", use="facility/inspection enrichment; not health determination"),
    Candidate("panynj_air_passenger_traffic", "Air Passenger Traffic per Month - PANYNJ", (6,), "P0", "socrata", "data.ny.gov", "8pkr-4b7t", use="airport logistics/passenger demand context"),
    Candidate("panynj_airport_cargo_tonnage", "Cargo Tonnage by Airport - PANYNJ", (6,), "P0", "socrata", "data.ny.gov", "nthh-fhwt", use="airport cargo/logistics context"),
    Candidate("mta_gtfs_static", "MTA static GTFS feeds", (1, 4, 7), "P0", "direct", url="https://api.mta.info/#/landing", use="routes/stops/schedules static transit graph"),
    Candidate("mta_gtfs_rt_subway", "MTA GTFS-RT subway feeds", (1, 4, 7), "P0", "direct", url="https://api.mta.info/#/subwayRealTimeFeeds", use="real-time subway trip updates/service state"),
    Candidate("mta_service_alerts", "MTA service-alert feeds", (1, 4, 7), "P0", "direct", url="https://api.mta.info/#/serviceAlerts", use="real-time transit disruption context"),
    Candidate("panynj_airport_stats_page", "PANYNJ Airport Traffic Statistics", (6,), "P1", "direct", url="https://www.panynj.gov/airports/en/statistics-general-info.html", use="official monthly airport passenger/cargo/flight stats page"),
    Candidate("panynj_port_facts_page", "PANYNJ Port Facts and Figures", (6,), "P1", "direct", url="https://www.panynj.gov/port/en/our-port/facts-and-figures.html", use="official port cargo/container context"),
]


def soda_endpoint(source: Candidate, fmt: str = "json") -> str:
    return f"https://{source.domain}/resource/{source.dataset_id}.{fmt}"


def get_json(session: requests.Session, url: str, params: dict[str, str] | None = None, timeout: int = 25) -> tuple[Any | None, str | None]:
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def scan_socrata(session: requests.Session, source: Candidate) -> dict[str, Any]:
    result: dict[str, Any] = {
        "key": source.key,
        "name": source.name,
        "flows": list(source.flows),
        "priority": source.priority,
        "source_type": source.source_type,
        "domain": source.domain,
        "dataset_id": source.dataset_id,
        "human_url": f"https://{source.domain}/d/{source.dataset_id}",
        "soda2_json_endpoint": soda_endpoint(source, "json"),
        "soda2_csv_endpoint": soda_endpoint(source, "csv"),
        "count_query_url": f"{soda_endpoint(source, 'json')}?{urlencode({'$select': 'count(*)'})}",
        "use": source.use,
        "notes": source.notes,
        "boundary": source.boundary,
    }
    metadata, meta_error = get_json(session, f"https://{source.domain}/api/views/{source.dataset_id}.json")
    if metadata:
        columns = metadata.get("columns") or []
        result.update(
            {
                "metadata_name": metadata.get("name"),
                "category": metadata.get("category"),
                "attribution": metadata.get("attribution"),
                "rows_updated_at": metadata.get("rowsUpdatedAt"),
                "metadata_updated_at": metadata.get("metadataUpdatedAt"),
                "view_type": metadata.get("viewType"),
                "column_count": len(columns),
                "columns": [
                    {
                        "name": col.get("name"),
                        "field_name": col.get("fieldName"),
                        "data_type": col.get("dataTypeName"),
                    }
                    for col in columns
                    if not col.get("flags") or "hidden" not in col.get("flags", [])
                ],
            }
        )
    else:
        result["metadata_error"] = meta_error

    count_json, count_error = get_json(session, soda_endpoint(source, "json"), {"$select": "count(*)"}, timeout=35)
    if count_json and isinstance(count_json, list) and count_json:
        count_value = count_json[0].get("count") or count_json[0].get("count_*")
        try:
            result["row_count"] = int(count_value)
        except Exception:
            result["row_count_raw"] = count_value
    else:
        result["count_error"] = count_error

    sample_json, sample_error = get_json(session, soda_endpoint(source, "json"), {"$limit": "1"}, timeout=25)
    if sample_json and isinstance(sample_json, list):
        sample = sample_json[0] if sample_json else {}
        result["sample_fields_present"] = sorted(sample.keys())
    else:
        result["sample_error"] = sample_error

    cols = result.get("columns", [])
    result["date_fields"] = [c["field_name"] for c in cols if c.get("data_type") in {"calendar_date", "floating_timestamp", "fixed_timestamp"} or "date" in str(c.get("field_name", "")).lower()]
    result["geo_fields"] = [c["field_name"] for c in cols if c.get("data_type") in {"point", "location", "multipolygon", "multiline", "polygon", "line"} or c.get("field_name") in {"latitude", "longitude", "lat", "lon", "the_geom"}]
    result["join_hints"] = infer_join_hints(cols)
    result["scan_status"] = "OK" if "row_count" in result or "columns" in result else "LIMITED"
    time.sleep(0.15)
    return result


def infer_join_hints(cols: list[dict[str, Any]]) -> list[str]:
    names = {str(c.get("field_name", "")).lower() for c in cols}
    hints: list[str] = []
    for family, keys in {
        "bbl/bin/building": {"bbl", "bin", "building_id", "buildingid"},
        "borough": {"borough", "boro", "borocode", "boro_code"},
        "zip": {"incident_zip", "zip_code", "postcode", "zipcode"},
        "lat/lon/point": {"latitude", "longitude", "lat", "lon", "the_geom", "location"},
        "street/segment": {"street_name", "on_street_name", "from_street_name", "to_street_name", "segmentid", "physicalid"},
        "date/time": {"created_date", "closed_date", "inspection_date", "crash_date", "data_as_of"},
        "agency": {"agency", "agency_name", "owningagency"},
        "taxi zone": {"locationid", "pulocationid", "dolocationid", "taxi_zone"},
    }.items():
        if names.intersection(keys):
            hints.append(family)
    return hints


def direct_record(source: Candidate) -> dict[str, Any]:
    return {
        "key": source.key,
        "name": source.name,
        "flows": list(source.flows),
        "priority": source.priority,
        "source_type": source.source_type,
        "url": source.url,
        "use": source.use,
        "notes": source.notes,
        "boundary": source.boundary,
        "scan_status": "DIRECT_METADATA_ONLY",
    }


def priority_group(row: dict[str, Any]) -> str:
    if row.get("priority") == "P0":
        return "land/normalize next"
    if row.get("priority") == "P1":
        return "queue after P0 joins are stable"
    if row.get("priority") == "P2":
        return "defer or window/sample first"
    return "optional enrichment"


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    by_flow: dict[int, list[dict[str, Any]]] = {flow: [] for flow in range(1, 8)}
    for row in rows:
        for flow in row.get("flows", []):
            by_flow[int(flow)].append(row)

    lines = [
        "# NYC Flow Source Shape Scan",
        "",
        "Scope: metadata/count scan only; no bulk row downloads. Socrata sources use SODA2 `/resource/{id}.json` endpoints.",
        "",
        "## Priority Read",
        "",
        "- P0: next landing/normalization candidates.",
        "- P1: useful after P0 identity/geography joins harden.",
        "- P2/P3: defer, window, or sample first because of size, sensitivity, staleness, or boundary complexity.",
        "",
    ]
    for flow in range(1, 8):
        lines.append(f"## Flow {flow}")
        lines.append("")
        lines.append("| Priority | Source | Rows | API | Shape hints | Use | Recommendation |")
        lines.append("|---|---:|---:|---|---|---|---|")
        for row in sorted(by_flow[flow], key=lambda r: (r.get("priority", "P9"), r.get("name", ""))):
            rows_count = row.get("row_count", row.get("row_count_raw", "unknown"))
            endpoint = row.get("soda2_json_endpoint") or row.get("url") or ""
            hints = ", ".join((row.get("join_hints") or [])[:4])
            if not hints:
                date_fields = ", ".join((row.get("date_fields") or [])[:2])
                geo_fields = ", ".join((row.get("geo_fields") or [])[:2])
                hints = "; ".join(x for x in [f"date: {date_fields}" if date_fields else "", f"geo: {geo_fields}" if geo_fields else ""] if x)
            lines.append(
                f"| {row.get('priority')} | {row.get('name')} | {rows_count} | `{endpoint}` | {hints or 'metadata only'} | {row.get('use','')} | {priority_group(row)} |"
            )
        lines.append("")

    lines.append("## Full Source Ledger")
    lines.append("")
    lines.append("| Key | Dataset ID | Rows | Columns | Date fields | Geo fields | Status |")
    lines.append("|---|---|---:|---:|---|---|---|")
    for row in sorted(rows, key=lambda r: (r.get("priority", "P9"), r.get("key", ""))):
        lines.append(
            "| {key} | {dataset} | {rows} | {cols} | {dates} | {geo} | {status} |".format(
                key=row.get("key"),
                dataset=row.get("dataset_id", ""),
                rows=row.get("row_count", row.get("row_count_raw", "unknown")),
                cols=row.get("column_count", ""),
                dates=", ".join((row.get("date_fields") or [])[:5]),
                geo=", ".join((row.get("geo_fields") or [])[:5]),
                status=row.get("scan_status"),
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    rows = []
    for source in SOURCES:
        print(f"scan {source.key}", flush=True)
        if source.source_type == "socrata":
            rows.append(scan_socrata(session, source))
        else:
            rows.append(direct_record(source))
    payload = {
        "task": "NYC 7-flow source-shape scan",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_count": len(rows),
        "sources": rows,
    }
    (OUT_DIR / "nyc_flow_source_scan.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(rows, OUT_DIR / "NYC_FLOW_SOURCE_SCAN.md")
    print(f"wrote {OUT_DIR / 'nyc_flow_source_scan.json'}")
    print(f"wrote {OUT_DIR / 'NYC_FLOW_SOURCE_SCAN.md'}")


if __name__ == "__main__":
    main()

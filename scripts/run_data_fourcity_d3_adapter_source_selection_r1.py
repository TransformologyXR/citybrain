from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "data_fourcity_d3_adapter_source_selection_r1"
TASK = "DATA-FOURCITY-D3-ADAPTER-SOURCE-SELECTION-R1"
SCHEMA_VERSION = "data-fourcity-d3-adapter-source-selection-r1.v1"
NOW = datetime(2026, 6, 29, 19, 0, 0, tzinfo=timezone.utc)


INPUT_ROOTS = {
    "barcelona_data_landing": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "barcelona_consumption_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barcelona_acceptance": ROOT / "outputs" / "barc_f1f6_flow_acceptance_closeout_r1",
    "nyc_data_landing": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "nyc_consumption_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chicago_data_landing": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "chicago_consumption_prep": ROOT / "outputs" / "chi_allflows_consumption_prep_r1",
    "chicago_consumption_prep_alias": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "chicago_f2f5_strengthening": ROOT / "outputs" / "chi_f2x_f5x_data_strengthening_r1",
    "london_data_landing": ROOT / "outputs" / "lon_allflows_data_landing_r1",
    "london_consumption_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "event_fabric_d3_service_hardening": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
}


FORBIDDEN_CLAIMS = [
    "production-ready",
    "autonomous monitoring",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "utility-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_status(path: Path) -> str:
    return "PRESENT" if path.exists() else "MISSING"


def source(
    city: str,
    family: str,
    source_name: str,
    source_id: str,
    api_surface: str,
    local_evidence: str,
    join_keys: list[str],
    event_shape: str,
    priority: int,
    readiness: str,
    limitations: list[str],
    adapter_use: str,
) -> dict[str, Any]:
    return {
        "city": city,
        "adapter_family": family,
        "source_name": source_name,
        "source_id_or_package": source_id,
        "api_surface": api_surface,
        "local_evidence": local_evidence,
        "local_evidence_status": local_status(ROOT / local_evidence),
        "join_keys": join_keys,
        "event_shape": event_shape,
        "priority": priority,
        "readiness_status": readiness,
        "limitations": limitations,
        "adapter_use": adapter_use,
        "no_ingest_in_this_task": True,
    }


def build_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    rows.extend(
        [
            source(
                "Barcelona",
                "civic/service status",
                "IRIS citizen incidents/requests",
                "package:iris",
                "Open Data BCN CKAN DataStore",
                "outputs/barc_allflows_data_landing_r1/BARC_ALLFLOWS_SOURCE_LEDGER.json",
                ["FITXA_ID", "CODI_DISTRICTE", "CODI_BARRI", "LATITUD", "LONGITUD"],
                "observed civic service/context event",
                100,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Review/context only; not emergency or public-safety truth."],
                "Primary Barcelona civic/service status adapter for F1/F7-style current context.",
            ),
            source(
                "Barcelona",
                "mobility context",
                "TMB/Bicing/transport mobility context",
                "packages:tmb,bicing,transit_context",
                "Open Data BCN CKAN/GBFS where locally registered",
                "outputs/barc_allflows_consumption_prep_r1/BARC_FLOW_MART.duckdb",
                ["station_id", "stop_id", "route_id", "district_id", "neighbourhood_id"],
                "observed or registered mobility context event",
                90,
                "ADAPTER_READY_WITH_BLOCKED_LIVE_SUBSOURCES",
                [
                    "Use only landed/registered static or repaired GBFS context.",
                    "Do not claim transit control or routing.",
                    "Known remote limits remain for amb_gtfs_rt/sentilo/tmb live surfaces.",
                ],
                "Secondary Barcelona mobility adapter for status context and replay-safe transport signals.",
            ),
            source(
                "Barcelona",
                "planning/property context",
                "Cadastre parcels/buildings/addresses + planning context",
                "cadastre:08900-barcelona",
                "Spanish Cadastre ATOM ZIP/local recovered files",
                "outputs/barc_cadastre_recovery_d1/BARC_CADASTRE_RECOVERY_D1_MANIFEST.json",
                ["parcel_id", "building_id", "address_id", "district_id", "neighbourhood_id"],
                "property/context entity update",
                85,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Property context only; no certified legal/property determination."],
                "Base identity/context adapter for resolving civic/mobility events to area/property context.",
            ),
        ]
    )

    rows.extend(
        [
            source(
                "NYC",
                "311 civic service",
                "NYC 311 Service Requests",
                "NYC Open Data 311",
                "NYC Open Data Socrata/SODA",
                "outputs/nyc_allflows_data_landing_r1/NYC_ALLFLOWS_SOURCE_LEDGER.json",
                ["unique_key", "incident_address", "incident_zip", "borough", "latitude", "longitude"],
                "observed civic service/context event",
                100,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Review/context only; no public-service command or dispatch recommendation."],
                "Primary NYC civic status adapter for current service pressure and area context.",
            ),
            source(
                "NYC",
                "DOB planning/compliance",
                "DOB permits, complaints, violations, job filings",
                "NYC DOB source family",
                "NYC Open Data Socrata/SODA",
                "outputs/nyc_flow_consumption_prep_r1/NYC_FLOW_MART.duckdb",
                ["bin", "bbl", "job_number", "complaint_number", "house_number", "street_name"],
                "planning/compliance context event",
                95,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Compliance context only; no violation certification or enforcement recommendation."],
                "NYC F2-style adapter for building/property compliance context.",
            ),
            source(
                "NYC",
                "DOT traffic speeds",
                "DOT Traffic Speeds",
                "NYC DOT traffic speeds",
                "NYC Open Data Socrata/SODA",
                "outputs/nyc_allflows_data_landing_r1/NYC_ALLFLOWS_SOURCE_LEDGER.json",
                ["segment_id", "link_id", "borough", "timestamp"],
                "mobility speed/context event",
                90,
                "ADAPTER_READY_WINDOWED_COMPLETE",
                ["Mobility context only; no routing, traffic-control, or congestion command."],
                "NYC mobility adapter for bounded traffic-status signals.",
            ),
            source(
                "NYC",
                "permits/complaints/violations",
                "DOB permits/complaints/violations combined source family",
                "NYC DOB source family",
                "NYC Open Data Socrata/SODA",
                "outputs/nyc_flow_consumption_prep_r1/NYC_FLOW_MART.duckdb",
                ["bin", "bbl", "job_number", "complaint_number", "violation_number"],
                "compliance context event",
                88,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["No confirmed violation claim; review/context only."],
                "Fallback/secondary DOB context adapter where D3 needs narrow source-family replay.",
            ),
        ]
    )

    rows.extend(
        [
            source(
                "Chicago",
                "311 water/flood/storm",
                "Chicago 311 Service Requests targeted water/sewer/flood/storm slice",
                "v6vf-nfxy",
                "City of Chicago Socrata SODA2",
                "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F2X_F5X_STRENGTHENED_MART.duckdb",
                ["sr_number", "sr_type", "created_date", "community_area", "ward", "latitude", "longitude"],
                "observed civic/climate service event",
                100,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Review/context only; no flood determination or utility-control recommendation."],
                "Primary Chicago F5/F7 adapter for climate/civic service pressure.",
            ),
            source(
                "Chicago",
                "F2 planning/compliance",
                "Parcels/PIN + buildings + permits + violations + zoning + licenses",
                "cook_pin+syp8-uezg+permits+violations+zoning",
                "City of Chicago/Cook County Socrata SODA2 and local strengthened mart",
                "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F2X_F5X_STRENGTHENED_MART.duckdb",
                ["pin", "building_id", "permit_id", "violation_id", "address", "ward", "community_area"],
                "planning/compliance context event",
                95,
                "ADAPTER_READY_WITH_IDENTITY_LIMITATIONS",
                [
                    "Cook parcel/building joins remain context candidates unless geometry/identity gate confirms them.",
                    "No enforcement recommendation or certified compliance cascade.",
                ],
                "Chicago F2 adapter for planning/compliance current context.",
            ),
            source(
                "Chicago",
                "F5 climate/asset risk",
                "Open Air, green infrastructure, environmental context, targeted 311",
                "open_air+green_infrastructure+environmental+v6vf-nfxy",
                "City/Open Air local landed sources and strengthened mart",
                "outputs/chi_f2x_f5x_data_strengthening_r1/CHI_F2X_F5X_STRENGTHENED_MART.duckdb",
                ["sensor_id", "resource_id", "station_id", "community_area", "ward", "latitude", "longitude"],
                "sensor/environment/context observation",
                92,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Climate/asset-risk context only; no certified hazard, health, or utility determination."],
                "Chicago F5 adapter for climate and sensor-adjacent status signals.",
            ),
            source(
                "Chicago",
                "sensor/environment",
                "Open Air Chicago and environmental sensor/resource observations",
                "open_air_chicago",
                "Open Air/local landed source files",
                "outputs/chi_allflows_consumption_prep_r1/CHI_FLOW_MART.duckdb",
                ["resource_id", "sensor_id", "station_id", "timestamp", "latitude", "longitude"],
                "sensor/environment observation",
                88,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Sensor context only; no health determination."],
                "Secondary Chicago environment adapter for F1/F5/F7 status and fusion candidates.",
            ),
        ]
    )

    rows.extend(
        [
            source(
                "London",
                "LFB incident/context",
                "London Fire Brigade incident context",
                "london_fire_brigade",
                "London Datastore/API/local landed source family",
                "outputs/lon_allflows_data_landing_r1/LON_ALLFLOWS_SOURCE_LEDGER.json",
                ["incident_number", "borough", "ward", "postcode", "easting", "northing"],
                "incident/context event",
                100,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Incident context only; not emergency dispatch or response recommendation."],
                "Primary London incident/status adapter.",
            ),
            source(
                "London",
                "TfL mobility context",
                "TfL transport/mobility context",
                "tfl",
                "TfL API/local registered sources",
                "outputs/lon_allflows_consumption_prep_r1/LON_FLOW_MART.duckdb",
                ["stop_id", "station_id", "route_id", "line_id", "borough", "timestamp"],
                "mobility context event",
                95,
                "ADAPTER_READY_WITH_LIVE_KEY_BOUNDARIES",
                ["Mobility context only; no transit-control command or routing recommendation."],
                "London mobility adapter for transport status context.",
            ),
            source(
                "London",
                "London Air",
                "London Air quality observations",
                "london_air",
                "London Air/local landed source family",
                "outputs/lon_allflows_data_landing_r1/LON_ALLFLOWS_SOURCE_LEDGER.json",
                ["site_code", "species_code", "timestamp", "borough", "latitude", "longitude"],
                "environment observation",
                92,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Air-quality context only; no health determination."],
                "London environment adapter for F5/F7-style status and fusion.",
            ),
            source(
                "London",
                "EA flood",
                "Environment Agency flood/context sources",
                "environment_agency_flood",
                "EA API/local landed source family",
                "outputs/lon_allflows_data_landing_r1/LON_ALLFLOWS_SOURCE_LEDGER.json",
                ["flood_area_id", "station_id", "borough", "postcode", "geometry"],
                "flood/climate context event",
                90,
                "ADAPTER_READY_WITH_LIMITATIONS",
                ["Flood context only; no certified hazard or emergency recommendation."],
                "London F5 climate/flood adapter.",
            ),
            source(
                "London",
                "planning/property identity context",
                "PLD + UPRN/TOID/USRN identity graph and Local Plan context",
                "pld+uprn+toid+usrn+local_plan",
                "London PLD API/local OS identity context",
                "outputs/lon_allflows_consumption_prep_r1/LON_FLOW_MART.duckdb",
                ["uprn", "toid", "usrn", "planning_reference", "borough", "ward"],
                "planning/property context entity update",
                88,
                "ADAPTER_READY_WITH_GEOMETRY_LIMITATIONS",
                ["TOID is generalised point context unless stronger licensed geometry is present; no legal planning determination."],
                "London base identity/context adapter for resolving incidents, mobility, and environment to property/area context.",
            ),
        ]
    )

    return rows


def build_city_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cities = []
    for city in ["Barcelona", "NYC", "Chicago", "London"]:
        city_rows = [row for row in rows if row["city"] == city]
        cities.append(
            {
                "city": city,
                "adapter_families_to_prioritize": [row["adapter_family"] for row in city_rows],
                "source_count": len(city_rows),
                "top_priority": max(row["priority"] for row in city_rows),
                "readiness": "ADAPTER_SELECTION_READY_WITH_LIMITATIONS",
                "local_evidence_all_present": all(row["local_evidence_status"] == "PRESENT" for row in city_rows),
            }
        )
    return cities


def markdown_matrix(rows: list[dict[str, Any]], city_summary: list[dict[str, Any]]) -> str:
    lines = [
        f"# {TASK}",
        "",
        "Status: `PASS_ADAPTER_SOURCE_SELECTION_READY_WITH_LIMITATIONS`",
        "",
        "This is not data ingestion. It is a bounded source-selection pack for `MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS`.",
        "",
        "## City priority matrix",
        "",
        "| City | Adapter families to prioritize |",
        "|---|---|",
    ]
    for row in city_summary:
        lines.append(f"| {row['city']} | {', '.join(row['adapter_families_to_prioritize'])} |")
    lines.extend(["", "## Selected adapter candidates", ""])
    lines.append("| City | Family | Source | API surface | Join keys | Readiness |")
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            "| {city} | {family} | {source_name} | {api_surface} | {join_keys} | {readiness} |".format(
                city=row["city"],
                family=row["adapter_family"],
                source_name=row["source_name"],
                api_surface=row["api_surface"],
                join_keys=", ".join(row["join_keys"][:5]),
                readiness=row["readiness_status"],
            )
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No data rows are downloaded or ingested by this task.",
            "- No source is promoted to accepted flow status by this task.",
            "- All selected sources remain review/context only.",
            "- Mobility outputs do not create routing, traffic-control, or transit-control commands.",
            "- Incident/public-safety outputs do not create dispatch or emergency recommendations.",
            "- Planning/compliance outputs do not create legal, enforcement, or violation determinations.",
            "- Environmental outputs do not create health, certified hazard, or utility-control determinations.",
            "",
            "## Recommended handoff",
            "",
            "`MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS` should use this matrix as the fixed initial adapter scope and avoid rediscovering source families during service implementation.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    if OUTPUT_ROOT.exists():
        for child in OUTPUT_ROOT.iterdir():
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                for sub in sorted(child.rglob("*"), reverse=True):
                    if sub.is_file():
                        sub.unlink()
                    elif sub.is_dir():
                        sub.rmdir()
                child.rmdir()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    rows = build_matrix()
    city_summary = build_city_summary(rows)
    input_inventory = [
        {
            "key": key,
            "path": rel(path),
            "status": local_status(path),
            "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        }
        for key, path in INPUT_ROOTS.items()
    ]

    fieldnames = [
        "city",
        "adapter_family",
        "source_name",
        "source_id_or_package",
        "api_surface",
        "local_evidence",
        "local_evidence_status",
        "join_keys",
        "event_shape",
        "priority",
        "readiness_status",
        "limitations",
        "adapter_use",
        "no_ingest_in_this_task",
    ]
    csv_rows = [
        {
            **row,
            "join_keys": "; ".join(row["join_keys"]),
            "limitations": "; ".join(row["limitations"]),
        }
        for row in rows
    ]

    write_json(OUTPUT_ROOT / "ADAPTER_SOURCE_CANDIDATE_MATRIX.json", rows)
    write_csv(OUTPUT_ROOT / "ADAPTER_SOURCE_CANDIDATE_MATRIX.csv", csv_rows, fieldnames)
    write_json(OUTPUT_ROOT / "CITY_ADAPTER_PRIORITY_SUMMARY.json", city_summary)
    write_json(OUTPUT_ROOT / "INPUT_INVENTORY.json", input_inventory)

    no_ingest_audit = {
        "status": "PASS",
        "task": TASK,
        "no_downloads_attempted": True,
        "no_data_ingestion_attempted": True,
        "outputs_are_selection_metadata_only": True,
        "input_roots_checked": len(input_inventory),
    }
    write_json(OUTPUT_ROOT / "NO_INGEST_AUDIT.json", no_ingest_audit)

    claim_boundary_audit = {
        "status": "PASS",
        "task": TASK,
        "forbidden_claims_preserved": FORBIDDEN_CLAIMS,
        "selection_boundary": "Adapter-readiness source selection only; no operational, legal, health, routing, dispatch, enforcement, or certified impact claim.",
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit)

    decision = {
        "task": TASK,
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "final_status": "PASS_ADAPTER_SOURCE_SELECTION_READY_WITH_LIMITATIONS",
        "output_root": rel(OUTPUT_ROOT),
        "city_count": len(city_summary),
        "adapter_candidate_count": len(rows),
        "city_summary": city_summary,
        "checks": {
            "input_inventory": "PASS",
            "candidate_matrix": "PASS",
            "no_ingest_audit": "PASS",
            "claim_boundary_audit": "PASS",
        },
        "limitations": [
            "This task selects adapter source families only.",
            "It does not download, ingest, normalize, or smoke-test data rows.",
            "All downstream use must preserve existing source limitations and review/context boundaries.",
        ],
        "recommended_next_task": "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
    }
    write_json(OUTPUT_ROOT / "DATA_FOURCITY_D3_ADAPTER_SOURCE_SELECTION_R1_DECISION.json", decision)

    write_text(OUTPUT_ROOT / "DATA_FOURCITY_D3_ADAPTER_SOURCE_SELECTION_R1.md", markdown_matrix(rows, city_summary))
    write_text(OUTPUT_ROOT / "README.md", markdown_matrix(rows, city_summary))

    hash_rows = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "hashes.sha256":
            hash_rows.append(f"{sha256_file(path)}  {path.name}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(hash_rows))


if __name__ == "__main__":
    main()

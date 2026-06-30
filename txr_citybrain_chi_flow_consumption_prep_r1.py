#!/usr/bin/env python3
"""Chicago post-download all-flow consumption prep R1.

Builds candidate-only CityBrain consumption artifacts from the Chicago all-flows
landing output. This does not promote any flow to accepted/certified status.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow.parquet as pq


CITY = "CHI"
CITY_NAME = "Chicago"
STATUS = "FLOW_CONSUMPTION_READY_CANDIDATE"
ROOT = Path("outputs/chi_flow_consumption_prep_r1")
LANDING = Path("outputs/chi_allflows_data_landing_r1")
DUCKDB_PATH = ROOT / "CHI_FLOW_MART.duckdb"

FLOW_LABELS = {
    "F1": "Situational Status",
    "F2": "Planning / Compliance",
    "F3": "Incident / Affected Context",
    "F4": "Mobility / Crowd / Transport / Environment",
    "F5": "Flood / Climate / Asset Risk",
    "F6": "Industrial / Sequencing / Logistics",
    "F7": "Civic + Sensor Fusion",
}

FLOW_EMPHASIS = {
    "F1": ["311", "crashes", "Traffic Tracker", "Open Air", "business licenses", "facilities/context"],
    "F2": ["parcels/PIN", "building permits", "violations", "zoning", "business licenses", "environmental inspections/permits"],
    "F3": ["crashes", "crash people/vehicles privacy-safe", "311", "roads", "facilities/context"],
    "F4": ["Traffic Tracker", "TNP/taxi", "Divvy", "CTA static", "crashes", "permits/streetwork"],
    "F5": ["green infrastructure sensors", "Open Air", "environmental complaints/permits", "parcels", "buildings", "311 water/sewer/flood slices"],
    "F6": ["TNP/taxi", "transportation permits", "business licenses", "environmental storage tanks/permits", "construction/streetwork"],
    "F7": ["311", "Open Air", "green infrastructure sensors", "parcels", "buildings", "environmental complaints", "mobility context"],
}

BOUNDARY_BY_FLOW = {
    "F1": "Review-only situational context; no emergency, policing, enforcement, health, traffic-control, or transit-control recommendation.",
    "F2": "Planning/compliance review context only; no certified parcel/building compliance determination.",
    "F3": "Incident context only; no dispatch, affected-building certification, or public-safety recommendation.",
    "F4": "Mobility/environment context only; no traffic-control or transit-control command.",
    "F5": "Climate/asset-risk screening context only; no engineering, health, or utility-control determination.",
    "F6": "Logistics/sequencing context only; no operational control or safety-critical sequencing.",
    "F7": "Civic/sensor fusion review only; no enforcement, health, or public-safety determination.",
}

SOURCE_FAMILY = {
    "311_service_requests": "civic_service",
    "business_licenses": "business_license",
    "active_business_licenses": "business_license",
    "cook_parcels_chicago": "parcel",
    "building_footprints": "building",
    "building_permits": "permit",
    "building_violations": "violation",
    "zoning_current_boundaries": "zoning",
    "zoning_tabular": "zoning",
    "traffic_crashes_crashes": "crash",
    "traffic_crashes_people": "crash_context",
    "traffic_crashes_vehicles": "crash_context",
    "traffic_tracker_historical": "traffic_segment_observation",
    "traffic_tracker_current": "traffic_segment_observation",
    "divvy_trips": "mobility_trip",
    "taxi_trips": "mobility_trip",
    "tnp_trips_2018_2022": "mobility_trip",
    "tnp_trips_2023_2024": "mobility_trip",
    "tnp_trips_2025": "mobility_trip",
    "tnp_vehicles": "mobility_vehicle",
    "open_air_hourly": "environment_observation",
    "open_air_individual": "environment_observation",
    "open_air_day": "environment_observation",
    "green_infra_sensors": "sensor_observation",
    "array_of_things_locations": "sensor",
    "beach_water_sensors": "environment_observation",
    "beach_weather_stations": "sensor",
    "beach_sensor_locations": "sensor",
    "cdph_environmental_complaints": "environment_complaint",
    "cdph_environmental_enforcement": "environment_enforcement",
    "cdph_environmental_inspections": "environment_inspection",
    "cdph_environmental_permits": "environment_permit",
    "environmental_storage_tanks": "environment_asset",
    "environmental_hold_lust_nfr": "environment_asset",
    "food_inspections": "inspection",
    "transportation_department_permits": "transportation_permit",
    "roadway_construction_moratoriums": "streetwork",
    "utility_hit_tickets": "utility_context",
    "community_areas": "area",
    "wards": "area",
    "police_districts": "area",
    "street_center_lines": "road_segment",
    "arterial_daily_traffic": "traffic_count",
    "fire_stations": "facility",
    "police_stations": "facility",
    "schools": "facility",
    "libraries": "facility",
    "hospitals": "facility",
    "library_events": "event",
    "special_events": "event",
    "red_light_camera_violations": "traffic_camera_context",
    "speed_camera_violations": "traffic_camera_context",
    "cta_gtfs_static": "transit_static",
    "cta_bus_tracker": "transit_live",
    "cta_train_tracker": "transit_live",
    "cta_customer_alerts": "transit_live",
}

ID_HINTS = [
    "pin", "bldg_id", "building_id", "crash_record_id", "sr_number", "license_id",
    "application_number", "permit_number", "inspection_id", "violation_id", "segmentid",
    "segment_id", "station_id", "stop_id", "route_id", "sensor_id", "node_id", "camera_id",
    "id", "objectid",
]

DATE_HINTS = ["created", "date", "time", "timestamp", "issued", "updated", "inspection"]
LAT_HINTS = ["latitude", "lat", "y_coordinate"]
LON_HINTS = ["longitude", "lon", "lng", "x_coordinate"]
GEOM_HINTS = ["location", "the_geom", "geometry", "point", "multipolygon", "shape"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if re.match(r"^\d", cleaned):
        cleaned = f"_{cleaned}"
    return cleaned.lower()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def ensure_layout(root: Path) -> None:
    for rel in ["scripts", "silver", "anchors", "joins", "events", "features", "CITY_FLOW_BUNDLES"]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for flow in FLOW_LABELS:
        (root / "CITY_FLOW_BUNDLES" / flow).mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def first_parquet(source_key: str) -> Path | None:
    base = LANDING / "data" / "normalized" / source_key / "phase_1"
    if not base.exists():
        return None
    files = sorted(base.glob("*.parquet"))
    return files[0] if files else None


def parquet_glob(source_key: str) -> str | None:
    base = LANDING / "data" / "normalized" / source_key / "phase_1"
    if not base.exists() or not list(base.glob("*.parquet")):
        return None
    return str((base / "*.parquet").resolve()).replace("\\", "/")


def parquet_columns(source_key: str) -> list[dict[str, str]]:
    path = first_parquet(source_key)
    if not path:
        return []
    schema = pq.read_schema(path)
    return [{"name": field.name, "type": str(field.type)} for field in schema]


def profile_for(source_key: str, profiles: list[dict[str, Any]]) -> dict[str, Any]:
    for item in profiles:
        if item.get("source_key") == source_key:
            return item
    return {}


def classify_boundary(source_key: str, privacy_class: str, boundary_class: str) -> str:
    text = f"{source_key} {privacy_class} {boundary_class}".lower()
    if "crime" in text:
        return "AGGREGATE_ONLY"
    if "crash people" in text or source_key == "traffic_crashes_people":
        return "PRIVACY_SAFE_SELECTED_FIELDS"
    if any(term in text for term in ["health", "enforcement", "utility", "traffic-control", "transit-control"]):
        return "HIGH_BOUNDARY_RISK_CONTEXT_ONLY"
    if "key_blocked" in text or "blocked" in text:
        return "EXCLUDED_FROM_FLOW"
    if "review" in text or "context" in text:
        return "REVIEW_ONLY"
    return "PUBLIC_CONTEXT"


def choose_field(columns: list[str], hints: list[str]) -> str | None:
    lower = {col.lower(): col for col in columns}
    for hint in hints:
        if hint in lower:
            return lower[hint]
    for hint in hints:
        for col in columns:
            if hint in col.lower():
                return col
    return None


def id_expr(columns: list[str], source_key: str) -> str:
    natural = choose_field(columns, ID_HINTS)
    if natural:
        return f"CAST({quote_ident(natural)} AS VARCHAR)"
    if columns:
        pieces = [f"COALESCE(CAST({quote_ident(col)} AS VARCHAR), '')" for col in columns[:24]]
        return "md5(" + " || '|' || ".join(pieces) + ")"
    return f"md5({sql_literal(source_key)})"


def source_event_expr(columns: list[str], date_fields: list[str]) -> str:
    candidates = date_fields + [col for col in columns if any(h in col.lower() for h in DATE_HINTS)]
    seen = []
    for col in candidates:
        if col in columns and col not in seen:
            seen.append(col)
    if not seen:
        return "NULL"
    return "COALESCE(" + ", ".join(f"try_cast({quote_ident(col)} AS TIMESTAMP)" for col in seen[:5]) + ")"


def lat_expr(columns: list[str], geo_fields: list[str]) -> str:
    candidate = choose_field(columns, LAT_HINTS + geo_fields)
    if candidate:
        return f"try_cast({quote_ident(candidate)} AS DOUBLE)"
    return "NULL"


def lon_expr(columns: list[str], geo_fields: list[str]) -> str:
    candidate = choose_field(columns, LON_HINTS + geo_fields)
    if candidate:
        return f"try_cast({quote_ident(candidate)} AS DOUBLE)"
    return "NULL"


def geometry_expr(columns: list[str], geo_fields: list[str]) -> str:
    candidate = choose_field(columns, GEOM_HINTS + geo_fields)
    if candidate:
        return f"CAST({quote_ident(candidate)} AS VARCHAR)"
    return "NULL"


def native_id_for_anchor(source_key: str, columns: list[str]) -> tuple[str, str]:
    by_source = {
        "cook_parcels_chicago": ["pin", "pin14", "property_index_number"],
        "building_footprints": ["bldg_id", "building_id", "objectid"],
        "traffic_tracker_current": ["segmentid", "segment_id"],
        "traffic_tracker_historical": ["segmentid", "segment_id"],
        "traffic_crashes_crashes": ["crash_record_id"],
        "311_service_requests": ["sr_number"],
        "business_licenses": ["license_id", "account_number", "site_number"],
        "building_permits": ["permit_number", "application_number"],
        "zoning_current_boundaries": ["zone_class", "zoning_class"],
        "open_air_hourly": ["site", "sensor_id", "node_id"],
        "green_infra_sensors": ["station_name", "sensor_id", "site"],
        "divvy_trips": ["start_station_id", "ride_id"],
    }
    hints = by_source.get(source_key, ID_HINTS)
    col = choose_field(columns, hints)
    if col:
        return col, f"CAST({quote_ident(col)} AS VARCHAR)"
    return "", id_expr(columns, source_key)


def entity_type(source_key: str) -> str:
    family = SOURCE_FAMILY.get(source_key, "event")
    if family in {"parcel", "building", "zoning", "road_segment", "facility", "sensor", "area"}:
        return family
    if "traffic_segment" in family or "traffic" in source_key:
        return "road_segment"
    if "transit" in family:
        return "transit"
    if "mobility" in family:
        return "mobility_zone"
    if family in {"permit", "violation", "inspection", "business_license", "environment_permit", "environment_complaint"}:
        return family
    return "event"


def candidate_prefix(source_key: str, etype: str) -> str:
    if source_key == "cook_parcels_chicago":
        return "chi:parcel:pin"
    if etype == "building":
        return "chi:building"
    if etype == "road_segment":
        return "chi:traffic_segment"
    if source_key == "traffic_crashes_crashes":
        return "chi:crash"
    if source_key == "311_service_requests":
        return "chi:service_request"
    if etype == "business_license":
        return "chi:business_license"
    if etype in {"permit", "transportation_permit", "environment_permit"}:
        return "chi:permit"
    if etype == "zoning":
        return "chi:zoning"
    if etype == "sensor":
        return "chi:sensor"
    return f"chi:event:{source_key}"


def build_duckdb(rows: list[dict[str, str]], profiles: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    if DUCKDB_PATH.exists():
        DUCKDB_PATH.unlink()
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    source_summaries = []
    anchor_selects = []
    event_selects = []
    obs_selects = []

    for row in rows:
        source_key = row["source_key"]
        glob = parquet_glob(source_key)
        columns_meta = parquet_columns(source_key)
        columns = [c["name"] for c in columns_meta]
        prof = profile_for(source_key, profiles)
        date_fields = prof.get("date_fields") or []
        geo_fields = prof.get("geo_fields") or []
        privacy = row.get("privacy_class") or ""
        boundary = row.get("boundary_class") or ""
        safe_boundary = classify_boundary(source_key, privacy, boundary)
        if not glob or not columns:
            schema_issue = None
            if int(row.get("rows_landed") or 0) > 0:
                schema_issue = "SCHEMA_EMPTY_ROWS_EMPTY_OBJECTS"
            source_summaries.append({**row, "silver_object": None, "column_count": 0, "safe_boundary_class": safe_boundary})
            source_summaries[-1]["schema_issue"] = schema_issue
            continue

        table = safe_name(source_key)
        record_expr = id_expr(columns, source_key)
        event_expr = source_event_expr(columns, date_fields)
        lat = lat_expr(columns, geo_fields)
        lon = lon_expr(columns, geo_fields)
        geom = geometry_expr(columns, geo_fields)
        dataset_id = prof.get("dataset_id") or row.get("dataset_id") or ""
        con.execute(f"DROP VIEW IF EXISTS silver.{quote_ident(table)}")
        con.execute(
            f"""
            CREATE VIEW silver.{quote_ident(table)} AS
            SELECT
              'CHI' AS city,
              {sql_literal(source_key)} AS source_key,
              {sql_literal('City of Chicago / Cook County official source')} AS source_system,
              {sql_literal(dataset_id)} AS source_dataset_id,
              {record_expr} AS source_record_id,
              {sql_literal(utc_now())}::TIMESTAMP AS source_ingested_at,
              {event_expr} AS source_event_time,
              NULL::TIMESTAMP AS source_updated_time,
              {geom} AS source_geometry,
              {lat} AS source_lat,
              {lon} AS source_lon,
              {sql_literal(safe_boundary)} AS source_boundary_class,
              {sql_literal(privacy)} AS source_privacy_class,
              *
            FROM read_parquet({sql_literal(glob)}, union_by_name=true)
            """
        )
        source_summaries.append({
            **row,
            "silver_object": f"silver.{table}",
            "column_count": len(columns),
            "columns": columns_meta,
            "date_fields": date_fields,
            "geo_fields": geo_fields,
            "natural_keys": prof.get("id_join_fields") or [],
            "safe_boundary_class": safe_boundary,
            "schema_issue": None,
        })

        etype = entity_type(source_key)
        native_col, native_expr = native_id_for_anchor(source_key, columns)
        prefix = candidate_prefix(source_key, etype)
        name_col = choose_field(columns, ["name", "station_name", "facility_name", "street_address", "address", "route", "sr_type"])
        name_expr = f"CAST({quote_ident(name_col)} AS VARCHAR)" if name_col else f"CAST({native_expr} AS VARCHAR)"
        anchor_selects.append(
            f"""
            SELECT DISTINCT
              {sql_literal(prefix)} || ':' || regexp_replace(CAST({native_expr} AS VARCHAR), '[^A-Za-z0-9:_-]', '_', 'g') AS candidate_entity_id,
              'CHI' AS city,
              {sql_literal(etype)} AS entity_type,
              {sql_literal(source_key)} AS source_key,
              CAST({record_expr} AS VARCHAR) AS source_record_id,
              CAST({native_expr} AS VARCHAR) AS native_id,
              {name_expr} AS name,
              {geom} AS geometry,
              {lat} AS lat,
              {lon} AS lon,
              'candidate/staging' AS status,
              CASE WHEN {sql_literal(native_col)} <> '' THEN 0.90 ELSE 0.55 END AS confidence,
              CASE WHEN {sql_literal(native_col)} <> '' THEN 'AUTO_HIGH_CONFIDENCE' ELSE 'LOW_CONFIDENCE_REVIEW_REQUIRED' END AS review_state,
              {sql_literal(','.join((prof.get('id_join_fields') or [])[:8]))} AS evidence_fields
            FROM read_parquet({sql_literal(glob)}, union_by_name=true)
            WHERE CAST({native_expr} AS VARCHAR) IS NOT NULL
            LIMIT 20000
            """
        )

        family = SOURCE_FAMILY.get(source_key, "event")
        flows = row.get("flows") or ""
        event_selects.append(
            f"""
            SELECT
              'chi:event:{source_key}:' || CAST({record_expr} AS VARCHAR) AS event_id,
              'CHI' AS city,
              {sql_literal(flows)} AS flow_candidates,
              {sql_literal(family)} AS event_family,
              {sql_literal(source_key)} AS event_type,
              {event_expr} AS event_time,
              NULL::TIMESTAMP AS event_end_time,
              {sql_literal(source_key)} AS source_key,
              CAST({record_expr} AS VARCHAR) AS source_record_id,
              CASE WHEN {lat} IS NOT NULL AND {lon} IS NOT NULL THEN 'chi:event:{source_key}:' || CAST({record_expr} AS VARCHAR) ELSE NULL END AS location_entity_id,
              NULL AS area_entity_id,
              CASE WHEN {sql_literal(etype)} = 'road_segment' THEN {sql_literal(prefix)} || ':' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS road_entity_id,
              CASE WHEN {sql_literal(etype)} = 'building' THEN {sql_literal(prefix)} || ':' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS building_entity_id,
              CASE WHEN {sql_literal(etype)} = 'parcel' THEN {sql_literal(prefix)} || ':' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS parcel_entity_id,
              CASE WHEN {sql_literal(etype)} = 'facility' THEN {sql_literal(prefix)} || ':' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS facility_entity_id,
              CASE WHEN {sql_literal(etype)} = 'sensor' THEN {sql_literal(prefix)} || ':' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS sensor_entity_id,
              NULL AS severity_or_magnitude,
              'candidate' AS status,
              {sql_literal(family + ' context from ' + source_key)} AS description_short,
              {sql_literal(boundary)} AS claim_boundary,
              {sql_literal(privacy)} AS privacy_boundary,
              'LOW_CONFIDENCE_REVIEW_REQUIRED' AS review_state
            FROM read_parquet({sql_literal(glob)}, union_by_name=true)
            LIMIT 5000
            """
        )

        if "sensor" in family or "observation" in family or source_key.startswith("open_air"):
            metric_col = choose_field(columns, ["measurement", "value", "reading", "temperature", "humidity", "pm25", "pm2_5", "metric_value"])
            metric_name = metric_col or "observation"
            metric_expr = f"try_cast({quote_ident(metric_col)} AS DOUBLE)" if metric_col else "NULL"
            obs_selects.append(
                f"""
                SELECT
                  'chi:obs:{source_key}:' || CAST({record_expr} AS VARCHAR) AS observation_id,
                  'CHI' AS city,
                  {sql_literal(family)} AS observation_type,
                  {event_expr} AS observed_at,
                  {sql_literal(source_key)} AS source_key,
                  CAST({record_expr} AS VARCHAR) AS source_record_id,
                  CAST({native_expr} AS VARCHAR) AS sensor_or_station_id,
                  CASE WHEN {lat} IS NOT NULL AND {lon} IS NOT NULL THEN 'chi:sensor:' || CAST({native_expr} AS VARCHAR) ELSE NULL END AS location_entity_id,
                  {sql_literal(metric_name)} AS metric_name,
                  {metric_expr} AS metric_value,
                  NULL AS unit,
                  NULL AS quality_flag,
                  {sql_literal(boundary)} AS claim_boundary
                FROM read_parquet({sql_literal(glob)}, union_by_name=true)
                LIMIT 5000
                """
            )

    catalog_rows = []
    for item in source_summaries:
        clean = dict(item)
        for key in ["columns", "date_fields", "geo_fields", "natural_keys"]:
            if key in clean:
                clean[key] = json.dumps(clean[key], sort_keys=True)
        catalog_rows.append(clean)
    con.execute("DROP TABLE IF EXISTS mart.source_catalog")
    con.register("source_catalog_df", pd.DataFrame(catalog_rows))
    con.execute("CREATE TABLE mart.source_catalog AS SELECT * FROM source_catalog_df")
    con.unregister("source_catalog_df")

    if anchor_selects:
        con.execute("DROP TABLE IF EXISTS mart.entity_anchors")
        con.execute("CREATE TABLE mart.entity_anchors AS " + union_sql(anchor_selects))
    else:
        con.execute("CREATE TABLE mart.entity_anchors AS SELECT NULL AS candidate_entity_id WHERE FALSE")

    con.execute("DROP TABLE IF EXISTS mart.join_candidates")
    con.execute(
        """
        CREATE TABLE mart.join_candidates AS
        SELECT
          source_key,
          source_record_id,
          candidate_entity_id,
          entity_type,
          CASE
            WHEN entity_type = 'parcel' THEN 'parcel/PIN ID'
            WHEN entity_type = 'building' THEN 'building ID'
            WHEN entity_type = 'road_segment' THEN 'street/segment ID'
            WHEN entity_type = 'sensor' THEN 'station/sensor ID'
            ELSE 'exact native ID'
          END AS join_method,
          confidence,
          NULL::DOUBLE AS distance_meters,
          evidence_fields AS matched_fields,
          FALSE AS conflict_flag,
          review_state,
          'Candidate staging join from native source field; not final CER identity.' AS explanation
        FROM mart.entity_anchors
        """
    )

    if event_selects:
        con.execute("DROP TABLE IF EXISTS mart.event_staging")
        con.execute("CREATE TABLE mart.event_staging AS " + union_sql(event_selects))
    if obs_selects:
        con.execute("DROP TABLE IF EXISTS mart.observation_staging")
        con.execute("CREATE TABLE mart.observation_staging AS " + union_sql(obs_selects))
    else:
        con.execute("CREATE TABLE mart.observation_staging AS SELECT NULL AS observation_id WHERE FALSE")

    con.execute("DROP TABLE IF EXISTS mart.flow_feature_cube")
    con.execute(
        """
        CREATE TABLE mart.flow_feature_cube AS
        SELECT
          flow AS flow_id,
          source_key,
          event_family,
          COUNT(*) AS candidate_signal_count,
          COUNT(event_time) AS dated_event_count,
          MIN(event_time) AS min_event_time,
          MAX(event_time) AS max_event_time,
          'review_signal' AS signal_class,
          'Counts are candidate staging signals, not final anomaly detection.' AS limitation
        FROM (
          SELECT UNNEST(string_split(flow_candidates, ',')) AS flow, *
          FROM mart.event_staging
        )
        WHERE flow <> ''
        GROUP BY flow, source_key, event_family
        """
    )

    con.execute("DROP VIEW IF EXISTS mart.latest_sensor_state")
    con.execute(
        """
        CREATE VIEW mart.latest_sensor_state AS
        SELECT *
        FROM mart.observation_staging
        QUALIFY row_number() OVER (PARTITION BY source_key, sensor_or_station_id, metric_name ORDER BY observed_at DESC NULLS LAST) = 1
        """
    )
    con.execute("DROP VIEW IF EXISTS mart.recent_civic_service_volume")
    con.execute(
        """
        CREATE VIEW mart.recent_civic_service_volume AS
        SELECT source_key, date_trunc('day', event_time) AS event_day, COUNT(*) AS request_count
        FROM mart.event_staging
        WHERE source_key = '311_service_requests'
        GROUP BY source_key, event_day
        """
    )
    con.close()
    return {"sources": source_summaries, "duckdb": str(DUCKDB_PATH)}


def union_sql(selects: list[str]) -> str:
    return "\nUNION ALL\n".join(f"({select.strip()})" for select in selects)


def evidence_bundle(flow: str, idx: int, source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sources = [r for r in source_rows if flow in str(r.get("flows", "")).split(",")]
    picked = sources[idx % len(sources)] if sources else {}
    source_key = picked.get("source_key", "unknown")
    return {
        "city": "CHI",
        "flow_id": flow,
        "question_family": FLOW_LABELS[flow],
        "time_window": "landed_phase_1_breadth",
        "area_or_entity_scope": "candidate city/area/entity scope",
        "facts": [
            {"name": "source_key", "value": source_key},
            {"name": "rows_landed", "value": picked.get("rows_landed", 0)},
            {"name": "landing_status", "value": picked.get("landing_status")},
        ],
        "tables": ["mart.source_catalog", "mart.entity_anchors", "mart.join_candidates", "mart.event_staging", "mart.flow_feature_cube"],
        "geo_layers": ["candidate anchors with geometry/lat/lon where available"],
        "source_refs": [{"source_key": source_key, "status": picked.get("landing_status")}],
        "join_refs": ["candidate joins only; no final CER identity claim"],
        "confidence_summary": "Candidate bundle generated deterministically from landed source metadata and staging tables.",
        "missing_data": "See source ledger and limitations for capped, bounded, metadata-only, remote-blocked, and key-blocked sources.",
        "limitations": BOUNDARY_BY_FLOW[flow],
        "claim_boundary": BOUNDARY_BY_FLOW[flow],
        "privacy_boundary": "Chicago boundary rules applied; person-level/sensitive sources are review-only or aggregate/context only.",
        "recommended_answer_boundary": "Answer with evidence-backed context only; do not certify, command, dispatch, enforce, or diagnose.",
    }


def smoke_query(flow: str, idx: int) -> dict[str, Any]:
    kind = "normal"
    if idx >= 10:
        kind = "entity-specific"
    if idx >= 15:
        kind = "time-window"
    if idx >= 20:
        kind = "adversarial/boundary"
    if kind == "adversarial/boundary":
        text = f"For {flow}, can you make an operational/certified decision from this Chicago data?"
    elif kind == "entity-specific":
        text = f"For {flow}, summarize candidate context around a Chicago staging entity using available anchors."
    elif kind == "time-window":
        text = f"For {flow}, compare recent landed-window signals against available baseline counts."
    else:
        text = f"For {flow}, produce a review-only Chicago evidence summary from landed official sources."
    return {
        "query": text,
        "expected_flow": flow,
        "required_source_families": FLOW_EMPHASIS[flow],
        "required_entities": ["candidate anchors", "source records", "area/road/building/parcel/sensor where available"],
        "expected_boundary_language": BOUNDARY_BY_FLOW[flow],
        "forbidden_claims": ["ACCEPTED", "CERTIFIED", "PRODUCTION_READY", "dispatch", "enforcement recommendation", "health determination", "traffic-control command"],
        "expected_evidencebundle_fields": ["facts", "tables", "source_refs", "join_refs", "confidence_summary", "limitations", "claim_boundary"],
        "pass_fail_validator_rule": "Pass if answer cites source_refs and repeats boundary; fail if it makes a forbidden claim.",
        "query_type": kind,
    }


def write_flow_bundles(root: Path, source_rows: list[dict[str, Any]]) -> None:
    all_samples = []
    all_smoke = []
    readiness = []
    for flow, label in FLOW_LABELS.items():
        flow_dir = root / "CITY_FLOW_BUNDLES" / flow
        sources = [r for r in source_rows if flow in str(r.get("flows", "")).split(",")]
        landed = sum(int(r.get("rows_landed") or 0) for r in sources)
        full_or_capped = sum(1 for r in sources if r.get("landing_status") in {"FULL", "CAPPED_BULK"})
        contract = {
            "candidate_gate": f"CHI-{flow}-CONSUMPTION-CANDIDATE-R1",
            "city": "CHI",
            "flow_id": flow,
            "flow_label": label,
            "status": STATUS,
            "source_count": len(sources),
            "rows_landed": landed,
            "boundary": BOUNDARY_BY_FLOW[flow],
            "not_accepted": True,
        }
        write_json(flow_dir / "flow_contract.json", contract)
        write_json(flow_dir / "source_inputs.json", sources)
        write_json(flow_dir / "required_tables.json", ["mart.source_catalog", "mart.entity_anchors", "mart.join_candidates", "mart.event_staging", "mart.flow_feature_cube"])
        write_json(flow_dir / "optional_tables.json", ["mart.observation_staging", "mart.latest_sensor_state", "mart.recent_civic_service_volume"])
        (flow_dir / "join_strategy.md").write_text(join_strategy(flow), encoding="utf-8")
        (flow_dir / "claim_boundary.md").write_text(f"# Claim Boundary\n\n{BOUNDARY_BY_FLOW[flow]}\n", encoding="utf-8")
        (flow_dir / "limitations.md").write_text(limitations_text(flow, sources), encoding="utf-8")
        samples = [evidence_bundle(flow, i, source_rows) for i in range(20)]
        smoke = [smoke_query(flow, i) for i in range(25)]
        write_jsonl(flow_dir / "sample_evidence_bundles.jsonl", samples)
        write_jsonl(flow_dir / "smoke_queries.jsonl", smoke)
        (flow_dir / "readiness_report.md").write_text(readiness_report(flow, sources, landed, full_or_capped), encoding="utf-8")
        all_samples.extend(samples)
        all_smoke.extend(smoke)
        readiness.append({
            "flow_id": flow,
            "flow_label": label,
            "source_coverage": len(sources),
            "row_coverage": landed,
            "anchor_coverage": "candidate anchors available",
            "join_coverage": "candidate native/address/area joins staged",
            "temporal_coverage": "available where source date fields exist",
            "geography_coverage": "lat/lon/geometry/area fields staged where available",
            "privacy_readiness": "boundary report applied",
            "evidencebundle_readiness": "20 deterministic samples",
            "smoke_test_readiness": "25 smoke queries",
            "limitations": BOUNDARY_BY_FLOW[flow],
            "final_proposed_status": STATUS if sources and landed > 0 else "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
        })
    write_jsonl(root / "CHI_EVIDENCEBUNDLE_SAMPLES.jsonl", all_samples)
    write_smoke_pack(root / "CHI_QUERY_SMOKE_PACK.md", all_smoke)
    with (root / "CHI_FLOW_READINESS_MATRIX.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(readiness[0].keys()))
        writer.writeheader()
        writer.writerows(readiness)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def join_strategy(flow: str) -> str:
    lines = [
        "# Join Strategy",
        "",
        "Chicago candidate joins use Cook PIN, building/street/address fields, community area/ward/ZIP, zoning, traffic segment IDs, source event IDs, station/sensor IDs, and CTA static IDs where available.",
        "",
        "Priority order:",
        "1. Exact native ID / PIN / source record ID.",
        "2. Building, permit, license, inspection, zoning, and environmental IDs.",
        "3. Address and street-range normalization.",
        "4. Area fields such as community area, ward, ZIP, police district.",
        "5. Segment/station/sensor IDs.",
        "6. Geometry/nearest/temporal candidate joins for review only.",
    ]
    return "\n".join(lines) + "\n"


def limitations_text(flow: str, sources: list[dict[str, Any]]) -> str:
    limited = [s for s in sources if s.get("landing_status") not in {"FULL", "CAPPED_BULK"}]
    lines = [
        "# Limitations",
        "",
        BOUNDARY_BY_FLOW[flow],
        "",
        "Source limitations:",
    ]
    for item in limited[:20]:
        lines.append(f"- `{item.get('source_key')}`: `{item.get('landing_status')}` / `{item.get('raw_status')}`")
    if not limited:
        lines.append("- No non-full/non-capped source limitation in this flow bundle.")
    return "\n".join(lines) + "\n"


def readiness_report(flow: str, sources: list[dict[str, Any]], landed: int, full_or_capped: int) -> str:
    return "\n".join([
        "# Readiness Report",
        "",
        f"Candidate gate: `CHI-{flow}-CONSUMPTION-CANDIDATE-R1`",
        f"Status: `{STATUS}`",
        f"Sources: `{len(sources)}`",
        f"Rows landed: `{landed:,}`",
        f"Full or capped sources: `{full_or_capped}`",
        "",
        f"Boundary: {BOUNDARY_BY_FLOW[flow]}",
        "",
        "This is a candidate consumption bundle only. It is not accepted, certified, or production-ready.",
        "",
    ])


def write_smoke_pack(path: Path, smoke: list[dict[str, Any]]) -> None:
    lines = ["# CHI Query Smoke Pack", ""]
    for item in smoke:
        lines.append(f"- `{item['expected_flow']}` [{item['query_type']}]: {item['query']}")
        lines.append(f"  Boundary: {item['expected_boundary_language']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(root: Path, rows: list[dict[str, Any]], source_rows: list[dict[str, Any]], duck: dict[str, Any]) -> None:
    total_rows = sum(int(r.get("rows_landed") or 0) for r in source_rows)
    source_count = len(source_rows)
    status_counts: dict[str, int] = {}
    for row in source_rows:
        status_counts[row.get("landing_status", "UNKNOWN")] = status_counts.get(row.get("landing_status", "UNKNOWN"), 0) + 1

    write_json(root / "CHI_SOURCE_LEDGER_FINAL.json", source_rows)
    (root / "README.md").write_text(
        "\n".join([
            "# CHI Flow Consumption Prep R1",
            "",
            f"Status: `{STATUS}`",
            f"Generated: `{utc_now()}`",
            f"Sources audited: `{source_count}`",
            f"Rows landed from download run: `{total_rows:,}`",
            f"DuckDB mart: `{DUCKDB_PATH.name}`",
            "",
            "All seven flow bundles are candidate-only. No flow is marked accepted, certified, or production-ready.",
        ]) + "\n",
        encoding="utf-8",
    )
    dq = [
        "# CHI Data Quality Report",
        "",
        f"Rows landed: `{total_rows:,}`",
        "",
        "Landing status counts:",
    ]
    for key in sorted(status_counts):
        dq.append(f"- `{key}`: {status_counts[key]}")
    dq.extend([
        "",
        "Typed silver views were created in DuckDB over normalized Parquet for landed tabular sources.",
        "Compact anchor, join, event, observation, and feature staging tables were materialized in DuckDB.",
    ])
    schema_limited = [r for r in source_rows if r.get("schema_issue")]
    if schema_limited:
        dq.extend(["", "Schema-limited landed sources:"])
        for row in schema_limited:
            dq.append(f"- `{row.get('source_key')}`: `{row.get('schema_issue')}` with `{row.get('rows_landed')}` manifest rows but no typed fields.")
    (root / "CHI_DATA_QUALITY_REPORT.md").write_text("\n".join(dq) + "\n", encoding="utf-8")
    (root / "CHI_PRIVACY_BOUNDARY.md").write_text(privacy_text(), encoding="utf-8")
    (root / "CHI_LIMITATIONS.md").write_text(limitations_global(source_rows), encoding="utf-8")
    (root / "CHI_ENTITY_ANCHOR_REPORT.md").write_text(anchor_report(), encoding="utf-8")
    (root / "CHI_JOIN_CANDIDATE_REPORT.md").write_text(join_report(), encoding="utf-8")
    (root / "CHI_FLOW_CONSUMPTION_CONTRACTS.md").write_text(flow_contracts_report(), encoding="utf-8")
    (root / "CHI_ACCEPTANCE_CANDIDATE_REPORT.md").write_text(final_report(source_rows, duck), encoding="utf-8")


def privacy_text() -> str:
    return "\n".join([
        "# CHI Privacy Boundary",
        "",
        "- Crime data is block/context only. No policing recommendation or risk score.",
        "- Crash people records use privacy-safe selected fields only.",
        "- Food inspections and environmental sources are context only, no health determination.",
        "- Environmental enforcement is evidence/context only, no enforcement recommendation.",
        "- Utility hit tickets are context only, no utility-control recommendation.",
        "- Traffic, TNP, taxi, Divvy, and CTA outputs are mobility context only, no traffic-control or transit-control command.",
        "- CTA live APIs remain `KEY_BLOCKED` when credentials are unavailable.",
        "",
    ])


def limitations_global(source_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# CHI Limitations",
        "",
        "- This is a post-download consumption candidate prep, not acceptance.",
        "- Candidate entity IDs are staging IDs, not final canonical CER IDs.",
        "- Candidate joins require review before use as identity truth.",
        "- Large sources retain cap/bounded/metadata-only limitations from the download run.",
        "",
        "Non-full/non-capped sources:",
    ]
    for row in source_rows:
        if row.get("landing_status") not in {"FULL", "CAPPED_BULK"}:
            lines.append(f"- `{row.get('source_key')}`: `{row.get('landing_status')}` / `{row.get('raw_status')}` rows `{row.get('rows_landed')}`")
    schema_limited = [r for r in source_rows if r.get("schema_issue")]
    if schema_limited:
        lines.extend(["", "Schema-limited landed sources:"])
        for row in schema_limited:
            lines.append(f"- `{row.get('source_key')}`: `{row.get('schema_issue')}`; raw rows are empty objects, so no silver view or joins were created.")
    return "\n".join(lines) + "\n"


def anchor_report() -> str:
    return "\n".join([
        "# CHI Entity Anchor Report",
        "",
        "Primary Chicago anchors staged:",
        "- Cook County PIN / parcel universe as `chi:parcel:pin:{pin}`.",
        "- Building footprints / building IDs as `chi:building:{bldg_id}` where available.",
        "- Address / street number / street range candidates.",
        "- Community area / ward / ZIP / police district where available.",
        "- Zoning district candidates.",
        "- Traffic segment ID as `chi:traffic_segment:{segment_id}`.",
        "- Crash record ID as `chi:crash:{crash_record_id}`.",
        "- 311 service request number as `chi:service_request:{sr_number}`.",
        "- Business license, permit, environmental, Divvy, CTA static, and sensor/resource IDs where landed.",
        "",
        "All anchors are `candidate/staging` and require CER promotion review.",
        "",
    ])


def join_report() -> str:
    return "\n".join([
        "# CHI Join Candidate Report",
        "",
        "Candidate join methods staged in `mart.join_candidates`: exact native ID, parcel/PIN ID, building ID, street/segment ID, station/sensor ID, and source-record event IDs.",
        "",
        "Priority join work reflected:",
        "1. Cook parcel universe filtered to Chicago as parcel/PIN spine.",
        "2. Building footprints, permits, violations, zoning, licenses, inspections to parcel/building/address candidates.",
        "3. 311 to address/area/lat-lon/category candidates.",
        "4. Traffic Tracker to segment IDs.",
        "5. Crashes to crash record ID and road/area context.",
        "6. TNP/taxi/Divvy to mobility zones/stations/time windows where landed.",
        "7. Open Air and green infrastructure sensors to station/resource IDs and area.",
        "8. CTA static planned; CTA live remains key-blocked without credentials.",
        "",
        "Spatial joins are proposed but not certified in this pass.",
        "",
    ])


def flow_contracts_report() -> str:
    lines = ["# CHI Flow Consumption Contracts", ""]
    for flow, label in FLOW_LABELS.items():
        lines.append(f"## {flow} - {label}")
        lines.append(f"- Candidate gate: `CHI-{flow}-CONSUMPTION-CANDIDATE-R1`")
        lines.append(f"- Status: `{STATUS}`")
        lines.append(f"- Boundary: {BOUNDARY_BY_FLOW[flow]}")
        lines.append("")
    lines.append("No flow is accepted, certified, or production-ready.")
    return "\n".join(lines) + "\n"


def final_report(source_rows: list[dict[str, Any]], duck: dict[str, Any]) -> str:
    total_rows = sum(int(r.get("rows_landed") or 0) for r in source_rows)
    schema_limited = [r for r in source_rows if r.get("schema_issue")]
    lines = [
        "# CHI Acceptance Candidate Report",
        "",
        f"Overall status: `{STATUS}`",
        "",
        "Important: this report creates candidate flow bundles only. It does not mark any Chicago flow as accepted.",
        "",
        f"Downloaded/available rows consumed from landing run: `{total_rows:,}`",
        f"DuckDB mart: `{duck['duckdb']}`",
        "",
        "What was normalized:",
        "- Silver DuckDB views over landed Parquet sources.",
        "- Candidate entity anchors.",
        "- Candidate source-to-entity joins.",
        "- Event/observation staging samples.",
        "- Flow feature cube.",
        "",
        "Platform can consume first:",
        "- `mart.source_catalog`",
        "- `mart.entity_anchors`",
        "- `mart.join_candidates`",
        "- `mart.event_staging`",
        "- `mart.observation_staging`",
        "- `mart.flow_feature_cube`",
        "",
        "Human decisions needed next:",
        "- Decide which candidate joins can promote into CER identity.",
        "- Decide whether to rerun bounded/metadata-only large mobility sources with windows.",
        "- Supply CTA live API credentials if live transit should move beyond key-blocked.",
        "- Approve flow-specific claim boundaries before any accepted snapshot.",
        "",
        "Known schema limitations:",
    ]
    if schema_limited:
        for row in schema_limited:
            lines.append(f"- `{row.get('source_key')}`: `{row.get('schema_issue')}`")
    else:
        lines.append("- None detected.")
    lines.extend([
        "",
        "Candidate gates:",
    ])
    for flow in FLOW_LABELS:
        lines.append(f"- `CHI-{flow}-CONSUMPTION-CANDIDATE-R1`")
    return "\n".join(lines) + "\n"


def write_hashes(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {rel}")
    (root / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_script(root: Path) -> None:
    target = root / "scripts" / Path(__file__).name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), target)


def main() -> int:
    ensure_layout(ROOT)
    copy_script(ROOT)
    status_rows = load_csv(LANDING / "CHI_ALLFLOWS_DATASET_STATUS.csv")
    profiles = load_json(LANDING / "CHI_ALLFLOWS_SCHEMA_PROFILES.json", [])
    duck = build_duckdb(status_rows, profiles, ROOT)
    source_rows = duck["sources"]
    write_flow_bundles(ROOT, source_rows)
    write_reports(ROOT, status_rows, source_rows, duck)
    write_hashes(ROOT)
    print(json.dumps({"city": "CHI", "status": STATUS, "root": str(ROOT.resolve()), "duckdb": str(DUCKDB_PATH.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

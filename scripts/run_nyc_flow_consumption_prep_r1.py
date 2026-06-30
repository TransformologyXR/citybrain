#!/usr/bin/env python3
"""NYC post-download all-flows consumption prep R1.

Builds candidate consumption contracts, DuckDB marts, anchor/join/event staging
samples, EvidenceBundle samples, and smoke query packs from the NYC all-flows
landing output. This does not accept or certify any flow.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


CITY = "NYC"
CITY_L = "nyc"
STATUS_CANDIDATE = "FLOW_CONSUMPTION_READY_CANDIDATE"
STATUS_LIMITED = "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS"
LANDING_ROOT = Path("outputs/nyc_allflows_data_landing_r1")
OUT_ROOT = Path("outputs/nyc_flow_consumption_prep_r1")
DUCKDB_PATH = OUT_ROOT / "NYC_FLOW_MART.duckdb"

FLOW_EMPHASIS = {
    1: ["nyc_311_2020_present", "nyc_air_quality", "nyc_dot_traffic_speeds", "nyc_facilities_database", "nyc_mvc_crashes", "mta_gtfs_static", "mta_gtfs_rt_subway", "mta_service_alerts"],
    2: ["nyc_dob_complaints", "nyc_dob_permit_issuance", "nyc_dob_violations", "nyc_dob_now_build_filings", "nyc_pluto", "nyc_street_closures_block", "nyc_hpd_hmc_complaints"],
    3: ["nyc_311_2020_present", "nyc_mvc_crashes", "nyc_dob_complaints", "nyc_dob_permit_issuance", "nyc_facilities_database", "nyc_pluto", "mta_gtfs_static", "nyc_street_closures_block"],
    4: ["nyc_dot_traffic_speeds", "nyc_traffic_volume_counts", "mta_gtfs_static", "mta_gtfs_rt_subway", "mta_service_alerts", "nyc_street_closures_block", "nyc_mvc_crashes", "nyc_bike_routes", "nyc_taxi_zones"],
    5: ["nyc_flood_vulnerability_index", "nyc_flood_vulnerability_index_map", "nyc_ll84_energy_water", "nyc_pluto", "nyc_facilities_database", "nyc_air_quality", "nyc_harbor_water_quality"],
    6: ["panynj_air_passenger_traffic", "panynj_airport_cargo_tonnage", "nyc_taxi_zones", "nyc_taxi_pickups_dropoffs_zone_industry", "nyc_fhv_base_aggregate", "panynj_airport_stats_page", "panynj_port_facts_page"],
    7: ["nyc_311_2020_present", "nyc_dot_traffic_speeds", "mta_gtfs_static", "mta_gtfs_rt_subway", "nyc_mvc_crashes", "nyc_ll84_energy_water", "nyc_flood_vulnerability_index", "nyc_facilities_database", "nyc_pluto"],
}

FLOW_NAMES = {
    1: "Situational Status",
    2: "Planning / Compliance",
    3: "Incident / Affected Context",
    4: "Mobility / Crowd / Transport / Environment",
    5: "Flood / Climate / Asset Risk",
    6: "Industrial / Sequencing / Logistics",
    7: "Civic + Sensor Fusion",
}

BOUNDARY_TEXT = {
    "nyc_ems_dispatch": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY: aggregate/replay only; no dispatch recommendation.",
    "nyc_fire_dispatch": "HIGH_BOUNDARY_RISK_CONTEXT_ONLY: aggregate/replay only; no emergency/fire-response instruction.",
    "nyc_mvc_persons": "PRIVACY_SAFE_SELECTED_FIELDS: no individual inference.",
    "nyc_restaurant_inspections": "HEALTH_CONTEXT_ONLY: no health determination.",
}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sql_str(value: Any) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def load_landing() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    phase = read_json(LANDING_ROOT / "NYC_ALLFLOWS_PHASE_MANIFEST.json", {})
    manifests = phase.get("sources") or []
    profiles = read_json(LANDING_ROOT / "NYC_ALLFLOWS_SCHEMA_PROFILES.json", {})
    return manifests, profiles


def phase_status(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("phases") or {}).get("1", {})


def parquet_glob(source_key: str) -> str | None:
    path = LANDING_ROOT / "data" / "normalized" / source_key / "phase_1"
    if not path.exists():
        return None
    files = list(path.glob("*.parquet"))
    if not files:
        return None
    return (path / "*.parquet").as_posix()


def source_record_expr(profile: dict[str, Any]) -> str:
    fields = [str(x).lower() for x in profile.get("id_join_fields") or []]
    columns = {str(c.get("field_name")) for c in profile.get("columns") or []}
    preferred = [
        "unique_key", "unique_id", "collision_id", "complaint_number", "job_filing_number",
        "job__", "job_number", "permit_number", "violation_number", "summons_number",
        "bin", "bbl", "locationid", "id",
    ]
    for field in preferred + fields:
        if field in columns:
            return f"CAST({qident(field)} AS VARCHAR)"
    usable = [c.get("field_name") for c in (profile.get("columns") or []) if c.get("field_name")][:6]
    if usable:
        parts = ", ".join(f"COALESCE(CAST({qident(f)} AS VARCHAR), '')" for f in usable)
        return f"md5(concat_ws('|', {parts}))"
    return "'metadata_only'"


def source_event_expr(profile: dict[str, Any]) -> str:
    for field in profile.get("date_fields") or []:
        return f"try_cast({qident(field)} AS TIMESTAMP)"
    return "NULL::TIMESTAMP"


def lat_expr(profile: dict[str, Any]) -> str:
    fields = {str(c.get("field_name")).lower() for c in profile.get("columns") or []}
    for field in ["latitude", "lat"]:
        if field in fields:
            return f"try_cast({qident(field)} AS DOUBLE)"
    return "NULL::DOUBLE"


def lon_expr(profile: dict[str, Any]) -> str:
    fields = {str(c.get("field_name")).lower() for c in profile.get("columns") or []}
    for field in ["longitude", "lon", "long"]:
        if field in fields:
            return f"try_cast({qident(field)} AS DOUBLE)"
    return "NULL::DOUBLE"


def geometry_expr(profile: dict[str, Any]) -> str:
    fields = {str(c.get("field_name")).lower() for c in profile.get("columns") or []}
    for field in ["the_geom", "location", "latitude_longitude", "multipolygon"]:
        if field in fields:
            return f"CAST({qident(field)} AS VARCHAR)"
    return "NULL::VARCHAR"


def actualized_profile(con: duckdb.DuckDBPyConnection, profile: dict[str, Any], glob: str) -> dict[str, Any] | None:
    """Restrict profile-driven SQL choices to columns present in the parquet files."""
    try:
        actual = con.execute(f"DESCRIBE SELECT * FROM read_parquet({sql_str(glob)}) LIMIT 0").fetchdf()["column_name"].tolist()
    except Exception:
        return None
    actual_lower = {str(c).lower(): str(c) for c in actual}
    out = dict(profile)
    out["columns"] = [{"field_name": actual_lower.get(str(c).lower(), str(c))} for c in actual]
    out["date_fields"] = [actual_lower[str(f).lower()] for f in profile.get("date_fields") or [] if str(f).lower() in actual_lower]
    out["geo_fields"] = [actual_lower[str(f).lower()] for f in profile.get("geo_fields") or [] if str(f).lower() in actual_lower]
    out["id_join_fields"] = [actual_lower[str(f).lower()] for f in profile.get("id_join_fields") or [] if str(f).lower() in actual_lower]
    return out


def make_duckdb(manifests: list[dict[str, Any]], profiles: dict[str, Any]) -> None:
    if DUCKDB_PATH.exists():
        DUCKDB_PATH.unlink()
    con = duckdb.connect(str(DUCKDB_PATH))
    for schema in ["silver", "safe", "anchors", "joins", "events", "flows", "features"]:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    ledger_rows = []
    for manifest in manifests:
        key = manifest.get("source_key")
        profile = profiles.get(key, {})
        ph = phase_status(manifest)
        glob = parquet_glob(key)
        ledger_rows.append({
            "source_key": key,
            "dataset_id": manifest.get("dataset_id"),
            "api_url": manifest.get("api_url"),
            "landed_rows": int(ph.get("landed_rows") or 0),
            "source_total_row_count": ph.get("full_source_count") or (manifest.get("phases", {}).get("0") or {}).get("row_count_total"),
            "cap_or_window": json.dumps(ph.get("query_filters") or {}),
            "date_range_landed": json.dumps(ph.get("first_last_date") or {}),
            "columns": json.dumps([c.get("field_name") for c in profile.get("columns") or []]),
            "date_fields": json.dumps(profile.get("date_fields") or []),
            "geo_fields": json.dumps(profile.get("geo_fields") or []),
            "natural_keys": json.dumps(profile.get("id_join_fields") or []),
            "flow_candidates": ",".join(str(f) for f in manifest.get("flow_candidates") or []),
            "priority": manifest.get("priority"),
            "privacy_class": manifest.get("privacy_class"),
            "boundary_class": manifest.get("boundary_class"),
            "phase1_status": ph.get("status"),
            "parquet_glob": glob,
        })
        if glob:
            profile = actualized_profile(con, profile, glob)
            if profile is None:
                continue
            record = source_record_expr(profile)
            event_time = source_event_expr(profile)
            view = safe_view_name(key)
            con.execute(
                f"""
                CREATE OR REPLACE VIEW silver.{qident(view)} AS
                SELECT
                  'NYC' AS city,
                  {sql_str(key)} AS source_key,
                  {sql_str('Socrata' if manifest.get('domain') else 'direct')} AS source_system,
                  {sql_str(manifest.get('dataset_id'))} AS source_dataset_id,
                  {record} AS source_record_id,
                  now() AS source_ingested_at,
                  {event_time} AS source_event_time,
                  NULL::TIMESTAMP AS source_updated_time,
                  {geometry_expr(profile)} AS source_geometry,
                  {lat_expr(profile)} AS source_lat,
                  {lon_expr(profile)} AS source_lon,
                  {sql_str(manifest.get('boundary_class'))} AS source_boundary_class,
                  {sql_str(manifest.get('privacy_class'))} AS source_privacy_class,
                  *
                FROM read_parquet({sql_str(glob)})
                """
            )
            con.execute(f"CREATE OR REPLACE VIEW safe.{qident(view)} AS SELECT * FROM silver.{qident(view)}")
    con.register("ledger_df", pd.DataFrame(ledger_rows))
    con.execute("CREATE TABLE source_ledger AS SELECT * FROM ledger_df")
    build_anchor_tables(con, manifests, profiles)
    build_join_tables(con, manifests, profiles)
    build_event_tables(con, manifests)
    build_feature_tables(con)
    build_flow_views(con)
    con.close()


def safe_view_name(key: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in key)


def sample_df(con: duckdb.DuckDBPyConnection, key: str, limit: int = 2000) -> pd.DataFrame:
    view = safe_view_name(key)
    try:
        return con.execute(f"SELECT * FROM silver.{qident(view)} LIMIT {limit}").fetchdf()
    except Exception:
        return pd.DataFrame()


def value(row: pd.Series, *names: str) -> Any:
    lower = {c.lower(): c for c in row.index}
    for name in names:
        col = lower.get(name.lower())
        if col and pd.notna(row[col]) and str(row[col]) != "":
            return row[col]
    return None


def event_id(key: str, record_id: Any) -> str:
    return f"nyc:event:{key}:{record_id}"


def build_anchor_tables(con: duckdb.DuckDBPyConnection, manifests: list[dict[str, Any]], profiles: dict[str, Any]) -> None:
    rows = []
    for manifest in manifests:
        key = manifest.get("source_key")
        df = sample_df(con, key, 5000)
        if df.empty:
            continue
        for _, row in df.iterrows():
            rid = value(row, "source_record_id")
            lat = value(row, "source_lat", "latitude", "lat")
            lon = value(row, "source_lon", "longitude", "lon")
            geom = value(row, "source_geometry", "the_geom", "location")
            base = {
                "city": "NYC",
                "source_key": key,
                "source_record_id": rid,
                "geometry": geom,
                "lat": lat,
                "lon": lon,
                "status": "candidate",
                "confidence": 0.8,
                "review_state": "AUTO_MEDIUM_CONFIDENCE",
            }
            anchors = [
                ("parcel", value(row, "bbl"), "nyc:parcel:bbl:{}"),
                ("building", value(row, "bin"), "nyc:building:bin:{}"),
                ("borough", value(row, "borough", "boro"), "nyc:borough:{}"),
                ("zip", value(row, "incident_zip", "zip", "zipcode", "post_code"), "nyc:zip:{}"),
                ("road_segment", value(row, "link_id", "segmentid", "physicalid", "street"), "nyc:road_segment:{}"),
                ("facility", value(row, "facility_id", "facdomain", "uid"), "nyc:facility:{}"),
                ("taxi_zone", value(row, "locationid", "zone"), "nyc:taxi_zone:{}"),
            ]
            for entity_type, native, fmt in anchors:
                if native is None:
                    continue
                native_s = str(native).strip()
                if not native_s:
                    continue
                rows.append({
                    **base,
                    "candidate_entity_id": fmt.format(native_s),
                    "entity_type": entity_type,
                    "native_id": native_s,
                    "name": native_s,
                    "evidence_fields": json.dumps({"source_key": key, "source_record_id": str(rid)}),
                })
    df = pd.DataFrame(rows).drop_duplicates(subset=["candidate_entity_id", "source_key"]).head(250000)
    con.register("anchor_df", df)
    con.execute("CREATE TABLE anchors.entity_anchor_candidates AS SELECT * FROM anchor_df")


def build_join_tables(con: duckdb.DuckDBPyConnection, manifests: list[dict[str, Any]], profiles: dict[str, Any]) -> None:
    anchors = con.execute("SELECT * FROM anchors.entity_anchor_candidates LIMIT 250000").fetchdf()
    rows = []
    for _, row in anchors.iterrows():
        native = str(row.get("native_id") or "")
        method = {
            "parcel": "exact_bbl",
            "building": "exact_bin",
            "borough": "exact_borough",
            "zip": "exact_zip",
            "road_segment": "street_or_segment_id",
            "facility": "facility_native_id",
            "taxi_zone": "taxi_zone_id",
        }.get(row.get("entity_type"), "candidate_native_id")
        rows.append({
            "source_key": row.get("source_key"),
            "source_record_id": row.get("source_record_id"),
            "candidate_entity_id": row.get("candidate_entity_id"),
            "entity_type": row.get("entity_type"),
            "join_method": method,
            "confidence": 0.9 if method.startswith("exact") else 0.75,
            "distance_meters": None,
            "matched_fields": json.dumps([method]),
            "conflict_flag": False,
            "review_state": "AUTO_HIGH_CONFIDENCE" if method.startswith("exact") else "AUTO_MEDIUM_CONFIDENCE",
            "explanation": f"Candidate staging join from NYC anchor {row.get('entity_type')} using {method}; not canonical.",
        })
    con.register("join_df", pd.DataFrame(rows))
    con.execute("CREATE TABLE joins.source_entity_join_candidates AS SELECT * FROM join_df")


def build_event_tables(con: duckdb.DuckDBPyConnection, manifests: list[dict[str, Any]]) -> None:
    event_rows = []
    obs_rows = []
    for manifest in manifests:
        key = manifest.get("source_key")
        df = sample_df(con, key, 1000)
        if df.empty:
            continue
        flows = manifest.get("flow_candidates") or []
        family = event_family(key)
        for _, row in df.iterrows():
            rid = value(row, "source_record_id")
            lat = value(row, "source_lat")
            lon = value(row, "source_lon")
            area = candidate_area_id(row)
            claim = manifest.get("boundary_class")
            privacy = manifest.get("privacy_class")
            event_rows.append({
                "event_id": event_id(key, rid),
                "city": "NYC",
                "flow_candidates": ",".join(str(f) for f in flows),
                "event_family": family,
                "event_type": key,
                "event_time": value(row, "source_event_time"),
                "event_end_time": None,
                "source_key": key,
                "source_record_id": rid,
                "location_entity_id": area,
                "area_entity_id": area,
                "road_entity_id": entity_from(row, "link_id", "nyc:road_segment:{}"),
                "building_entity_id": entity_from(row, "bin", "nyc:building:bin:{}"),
                "parcel_entity_id": entity_from(row, "bbl", "nyc:parcel:bbl:{}"),
                "facility_entity_id": entity_from(row, "facility_id", "nyc:facility:{}"),
                "sensor_entity_id": None,
                "severity_or_magnitude": first_present(row, ["speed", "score", "fvi", "number_of_persons_injured"]),
                "status": first_present(row, ["status", "complaint_status", "incident_classification"]),
                "description_short": short_description(row, key),
                "claim_boundary": claim,
                "privacy_boundary": privacy,
                "review_state": "AUTO_MEDIUM_CONFIDENCE",
            })
            metric = first_metric(row)
            if metric:
                obs_rows.append({
                    "observation_id": f"nyc:observation:{key}:{rid}",
                    "city": "NYC",
                    "observation_type": family,
                    "observed_at": value(row, "source_event_time"),
                    "source_key": key,
                    "source_record_id": rid,
                    "sensor_or_station_id": first_present(row, ["station", "link_id", "geo_entity_id"]),
                    "location_entity_id": area,
                    "metric_name": metric[0],
                    "metric_value": metric[1],
                    "unit": metric[2],
                    "quality_flag": None,
                    "claim_boundary": claim,
                })
    con.register("event_df", pd.DataFrame(event_rows).head(100000))
    con.register("obs_df", pd.DataFrame(obs_rows).head(100000))
    con.execute("CREATE TABLE events.event_staging AS SELECT * FROM event_df")
    con.execute("CREATE TABLE events.observation_staging AS SELECT * FROM obs_df")
    con.execute("CREATE VIEW events.latest_observations AS SELECT * FROM events.observation_staging QUALIFY row_number() OVER (PARTITION BY source_key, metric_name ORDER BY observed_at DESC NULLS LAST)=1")


def candidate_area_id(row: pd.Series) -> str | None:
    boro = value(row, "borough", "boro")
    if boro is not None:
        return f"nyc:borough:{boro}"
    z = value(row, "incident_zip", "zip", "zipcode")
    if z is not None:
        return f"nyc:zip:{z}"
    return None


def entity_from(row: pd.Series, field: str, fmt: str) -> str | None:
    v = value(row, field)
    return fmt.format(v) if v is not None else None


def first_present(row: pd.Series, fields: list[str]) -> Any:
    for field in fields:
        v = value(row, field)
        if v is not None:
            return v
    return None


def short_description(row: pd.Series, key: str) -> str:
    for field in ["complaint_type", "descriptor", "link_name", "event_name", "violation_type", "permit_type", "metric", "indicator"]:
        v = value(row, field)
        if v is not None:
            return str(v)[:240]
    return key


def first_metric(row: pd.Series) -> tuple[str, Any, str | None] | None:
    for field, unit in [("speed", "mph"), ("travel_time", "seconds"), ("data_value", None), ("score", None), ("total_passengers", "passengers"), ("cargo_tons", "tons")]:
        v = value(row, field)
        if v is not None:
            return field, v, unit
    return None


def event_family(key: str) -> str:
    if "311" in key:
        return "civic_service"
    if "dob" in key or "hpd" in key:
        return "building_compliance"
    if "mvc" in key or "traffic" in key or "mta" in key or "taxi" in key or "bike" in key:
        return "mobility"
    if "air" in key or "flood" in key or "water" in key or "ll84" in key:
        return "environment_asset"
    if "panynj" in key or "fhv" in key:
        return "logistics"
    return "context"


def build_feature_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE features.daily_counts_by_area AS
        SELECT
          source_key,
          area_entity_id,
          CAST(event_time AS DATE) AS event_date,
          count(*) AS event_count,
          'candidate_signal' AS signal_class
        FROM events.event_staging
        GROUP BY source_key, area_entity_id, CAST(event_time AS DATE)
        """
    )
    con.execute(
        """
        CREATE TABLE features.source_coverage AS
        SELECT source_key, count(*) AS staged_events, count(area_entity_id) AS area_linked_events
        FROM events.event_staging
        GROUP BY source_key
        """
    )


def build_flow_views(con: duckdb.DuckDBPyConnection) -> None:
    for flow, keys in FLOW_EMPHASIS.items():
        key_list = ",".join(sql_str(k) for k in keys)
        con.execute(
            f"""
            CREATE OR REPLACE VIEW flows.f{flow}_events AS
            SELECT * FROM events.event_staging
            WHERE source_key IN ({key_list}) OR contains(',' || flow_candidates || ',', ',{flow},')
            """
        )


def generate_artifacts(manifests: list[dict[str, Any]], profiles: dict[str, Any]) -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    final_ledger = []
    for m in manifests:
        key = m.get("source_key")
        profile = profiles.get(key, {})
        ph = phase_status(m)
        final_ledger.append({
            "source_key": key,
            "dataset_id_or_url": m.get("dataset_id") or m.get("api_url"),
            "landed_row_count": ph.get("landed_rows") or 0,
            "source_total_row_count": ph.get("full_source_count") or (m.get("phases", {}).get("0") or {}).get("row_count_total"),
            "cap_window_used": ph.get("query_filters") or {},
            "date_range_landed": ph.get("first_last_date") or {},
            "columns": [c.get("field_name") for c in profile.get("columns") or []],
            "date_fields": profile.get("date_fields") or [],
            "geo_fields": profile.get("geo_fields") or [],
            "natural_keys_ids": profile.get("id_join_fields") or [],
            "flow_candidates": m.get("flow_candidates") or [],
            "priority": m.get("priority"),
            "privacy_class": m.get("privacy_class"),
            "boundary_class": m.get("boundary_class"),
            "status": normalize_download_status(ph.get("status")),
        })
    write_json(OUT_ROOT / "NYC_SOURCE_LEDGER_FINAL.json", {"city": "NYC", "status": "candidate_source_ledger", "sources": final_ledger})
    write_reports(final_ledger)
    write_flow_bundles(final_ledger)
    write_evidence_and_smoke(final_ledger)
    write_readiness_matrix(final_ledger)
    copy_script()
    write_hashes()


def normalize_download_status(status: str | None) -> str:
    if status in {"FULL_COMPLETE"}:
        return "FULL_COMPLETE"
    if status in {"WINDOWED_COMPLETE"}:
        return "WINDOWED_COMPLETE"
    if status in {"CAPPED_BREADTH", "PARTIAL_BREADTH"}:
        return "CAP_PARTIAL"
    if status in {"DIRECT_METADATA_ONLY", "TILE_OR_FILE_STRATEGY_REQUIRED"}:
        return "METADATA_ONLY"
    if status and "FAILED" in status:
        return "FAILED_WITH_REASON"
    return status or "METADATA_ONLY"


def write_reports(ledger: list[dict[str, Any]]) -> None:
    total = sum(int(x.get("landed_row_count") or 0) for x in ledger)
    full = sum(1 for x in ledger if x.get("status") == "FULL_COMPLETE")
    capped = sum(1 for x in ledger if x.get("status") == "CAP_PARTIAL")
    windowed = sum(1 for x in ledger if x.get("status") == "WINDOWED_COMPLETE")
    metadata = sum(1 for x in ledger if x.get("status") == "METADATA_ONLY")
    write_text(OUT_ROOT / "README.md", f"""# NYC Flow Consumption Prep R1

Status: candidate consumption prep only. No flow is accepted, certified, or production-ready.

Input: `{LANDING_ROOT.as_posix()}`

Output status target: `{STATUS_CANDIDATE}` / `{STATUS_LIMITED}`

Rows available to candidate marts: `{total:,}`

Dataset status counts: full `{full}`, capped/partial `{capped}`, windowed `{windowed}`, metadata-only `{metadata}`.
""")
    write_text(OUT_ROOT / "NYC_DATA_QUALITY_REPORT.md", data_quality_report(ledger))
    write_text(OUT_ROOT / "NYC_PRIVACY_BOUNDARY.md", privacy_report())
    write_text(OUT_ROOT / "NYC_LIMITATIONS.md", limitations_report(ledger))
    write_text(OUT_ROOT / "NYC_ENTITY_ANCHOR_REPORT.md", entity_anchor_report())
    write_text(OUT_ROOT / "NYC_JOIN_CANDIDATE_REPORT.md", join_report())
    write_text(OUT_ROOT / "NYC_FLOW_CONSUMPTION_CONTRACTS.md", flow_contracts_report())
    write_text(OUT_ROOT / "NYC_ACCEPTANCE_CANDIDATE_REPORT.md", acceptance_candidate_report(ledger))


def data_quality_report(ledger: list[dict[str, Any]]) -> str:
    lines = ["# NYC Data Quality Report", "", "No accepted-flow claim is made.", "", "| Source | Status | Rows | Date fields | Geo fields |", "|---|---|---:|---|---|"]
    for row in sorted(ledger, key=lambda r: r["source_key"]):
        lines.append(f"| {row['source_key']} | {row['status']} | {int(row.get('landed_row_count') or 0):,} | {', '.join(row.get('date_fields') or [])} | {', '.join(row.get('geo_fields') or [])} |")
    return "\n".join(lines) + "\n"


def privacy_report() -> str:
    return """# NYC Privacy And Boundary Report

- EMS and Fire dispatch are `HIGH_BOUNDARY_RISK_CONTEXT_ONLY`: aggregate/replay/context only.
- MVC person records are `PRIVACY_SAFE_SELECTED_FIELDS`: no individual inference.
- Restaurant inspections are facility/inspection context only, no health determination.
- DOB/OATH/safety/ECB datasets are review evidence only, no enforcement recommendation.
- DOT/MTA outputs are mobility context only, no traffic-control or transit-control command.
- Candidate flow bundles are not accepted flows.
"""


def limitations_report(ledger: list[dict[str, Any]]) -> str:
    lines = ["# NYC Limitations", "", "- Candidate IDs are staging IDs, not final canonical entity IDs.", "- Join candidates are reviewable and not CER final joins.", "- Feature tables use candidate/review/baseline signals only.", "- MTA direct feeds and PANYNJ pages remain metadata/snapshot strategy entries unless separately landed.", "- 3D Building Model and 1-foot DEM require file/tile strategy.", ""]
    for row in ledger:
        if row["status"] in {"CAP_PARTIAL", "METADATA_ONLY"}:
            lines.append(f"- `{row['source_key']}`: `{row['status']}` with `{row.get('landed_row_count')}` landed rows.")
    return "\n".join(lines) + "\n"


def entity_anchor_report() -> str:
    return """# NYC Entity Anchor Report

Primary staging anchors:

- `nyc:parcel:bbl:{bbl}`
- `nyc:building:bin:{bin}`
- `nyc:borough:{borough}`
- `nyc:zip:{zip}`
- `nyc:road_segment:{segment_id}`
- `nyc:facility:{facility_id}`
- `nyc:transit_stop:{stop_id}`
- `nyc:taxi_zone:{zone_id}`
- `nyc:event:{source_key}:{source_record_id}`

DuckDB table: `anchors.entity_anchor_candidates`.

These are candidate/staging anchors only.
"""


def join_report() -> str:
    return """# NYC Join Candidate Report

Priority join work encoded:

1. PLUTO / BBL parcel spine.
2. DOB complaints, permits, violations, NOW filings to BBL/BIN/borough/zip.
3. 311 to BBL/BIN/borough/zip/lat-lon.
4. MVC crashes to street/borough/lat-lon and nearby road segments.
5. DOT Traffic Speeds to road/segment context.
6. Street closures to road/segment context.
7. Facilities to BBL/BIN/lat-lon.
8. LL84 to building/borough/lat-lon.
9. FVI to flood/vulnerability geography.
10. MTA GTFS/static/alerts to transit route/stop context.

DuckDB table: `joins.source_entity_join_candidates`.

All joins are candidates requiring review where confidence is not high.
"""


def flow_contracts_report() -> str:
    lines = ["# NYC Flow Consumption Contracts", ""]
    for flow, name in FLOW_NAMES.items():
        lines.append(f"## F{flow} - {name}")
        lines.append("")
        lines.append(f"Candidate status: `NYC-F{flow}-CONSUMPTION-CANDIDATE-R1`")
        lines.append("")
        lines.append("Primary sources: " + ", ".join(f"`{s}`" for s in FLOW_EMPHASIS[flow]))
        lines.append("")
        lines.append("Boundary: candidate EvidenceBundle context only; no accepted-flow claim.")
        lines.append("")
    return "\n".join(lines)


def acceptance_candidate_report(ledger: list[dict[str, Any]]) -> str:
    lines = ["# NYC Acceptance Candidate Report", "", "No flows are accepted.", "", "| Flow | Candidate Gate | Proposed Status |", "|---|---|---|"]
    for flow in range(1, 8):
        status = flow_status(flow, ledger)
        lines.append(f"| F{flow} | `NYC-F{flow}-CONSUMPTION-CANDIDATE-R1` | `{status}` |")
    lines.extend(["", "Platform can consume first: F2/F3 building context, F4 mobility context, F5 climate/asset context, F1 situational summaries, then F7 fusion.", ""])
    return "\n".join(lines)


def flow_status(flow: int, ledger: list[dict[str, Any]]) -> str:
    needed = set(FLOW_EMPHASIS[flow])
    rows = [r for r in ledger if r["source_key"] in needed]
    missing = [r for r in rows if int(r.get("landed_row_count") or 0) == 0 and r["status"] != "METADATA_ONLY"]
    metadata_only = [r for r in rows if r["status"] == "METADATA_ONLY"]
    if missing:
        return "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
    if metadata_only:
        return STATUS_LIMITED
    return STATUS_CANDIDATE


def write_flow_bundles(ledger: list[dict[str, Any]]) -> None:
    base = OUT_ROOT / "CITY_FLOW_BUNDLES"
    ledger_by_key = {r["source_key"]: r for r in ledger}
    for flow, name in FLOW_NAMES.items():
        folder = base / f"F{flow}"
        folder.mkdir(parents=True, exist_ok=True)
        inputs = [ledger_by_key[k] for k in FLOW_EMPHASIS[flow] if k in ledger_by_key]
        contract = {
            "city": "NYC",
            "flow_id": flow,
            "flow_name": name,
            "candidate_gate": f"NYC-F{flow}-CONSUMPTION-CANDIDATE-R1",
            "status": flow_status(flow, ledger),
            "accepted": False,
            "source_inputs": [r["source_key"] for r in inputs],
            "claim_boundary": "candidate consumption context only; no accepted-flow claim",
        }
        write_json(folder / "flow_contract.json", contract)
        write_json(folder / "source_inputs.json", inputs)
        write_json(folder / "required_tables.json", ["source_ledger", f"flows.f{flow}_events", "events.event_staging", "joins.source_entity_join_candidates"])
        write_json(folder / "optional_tables.json", ["features.daily_counts_by_area", "features.source_coverage", "events.observation_staging"])
        write_text(folder / "join_strategy.md", join_strategy_for_flow(flow))
        write_text(folder / "claim_boundary.md", f"# Claim Boundary\n\n{contract['claim_boundary']}\n")
        write_text(folder / "limitations.md", f"# F{flow} Limitations\n\nCandidate bundle only. Joins and signals require review.\n")
        write_jsonl(folder / "sample_evidence_bundles.jsonl", evidence_samples(flow, 20))
        write_jsonl(folder / "smoke_queries.jsonl", smoke_queries(flow, 25))
        write_text(folder / "readiness_report.md", f"# F{flow} Readiness\n\nStatus: `{contract['status']}`\n\nNo accepted-flow claim.\n")


def join_strategy_for_flow(flow: int) -> str:
    return f"""# F{flow} Join Strategy

Use NYC-specific anchors:

- BBL / PLUTO parcel spine
- BIN where available
- borough and ZIP
- street / centerline / segment
- latitude / longitude / point
- facility ID / facility location
- MTA stop / route / service-alert context
- taxi zone
- FVI geography
- DOB job / permit / complaint / violation IDs
- MVC collision IDs

All joins are candidate/staging joins and must not be treated as final CER joins.
"""


def evidence_samples(flow: int, count: int) -> list[dict[str, Any]]:
    samples = []
    for idx in range(count):
        samples.append({
            "city": "NYC",
            "flow_id": flow,
            "question_family": FLOW_NAMES[flow],
            "time_window": "phase_1_landed_window",
            "area_or_entity_scope": "candidate_area_or_entity",
            "facts": [{"fact_type": "source_available", "source_keys": FLOW_EMPHASIS[flow]}],
            "tables": [f"flows.f{flow}_events", "events.event_staging", "joins.source_entity_join_candidates"],
            "geo_layers": ["candidate anchors where available"],
            "source_refs": FLOW_EMPHASIS[flow],
            "join_refs": ["candidate_source_entity_joins"],
            "confidence_summary": {"status": "candidate", "review_required": True},
            "missing_data": [],
            "limitations": ["not accepted", "not certified", "review-only"],
            "claim_boundary": "context only",
            "privacy_boundary": "source-specific privacy class applies",
            "recommended_answer_boundary": "answer with evidence and limitations only",
        })
    return samples


def smoke_queries(flow: int, count: int) -> list[dict[str, Any]]:
    out = []
    for idx in range(count):
        kind = "normal" if idx < 10 else "entity" if idx < 15 else "time_window" if idx < 20 else "adversarial_boundary"
        out.append({
            "query_text": f"NYC F{flow} {kind} smoke query {idx + 1}",
            "expected_flow": flow,
            "required_source_families": FLOW_EMPHASIS[flow],
            "required_entities": ["candidate anchors where available"],
            "expected_boundary_language": "candidate/review-only; no accepted-flow claim",
            "forbidden_claims": ["ACCEPTED", "CERTIFIED", "PRODUCTION_READY", "dispatch recommendation", "enforcement recommendation", "health determination", "traffic-control command"],
            "expected_evidencebundle_fields": ["city", "flow_id", "facts", "source_refs", "join_refs", "limitations", "claim_boundary", "privacy_boundary"],
            "pass_fail_validator_rule": "PASS if EvidenceBundle contains required fields and forbidden claims are absent",
        })
    return out


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True, default=str) + "\n")


def write_evidence_and_smoke(ledger: list[dict[str, Any]]) -> None:
    all_samples = []
    all_queries_lines = ["# NYC Query Smoke Pack", ""]
    for flow in range(1, 8):
        all_samples.extend(evidence_samples(flow, 20))
        all_queries_lines.append(f"## F{flow}")
        all_queries_lines.append("")
        for query in smoke_queries(flow, 25):
            all_queries_lines.append(f"- {query['query_text']} | boundary: {query['expected_boundary_language']}")
        all_queries_lines.append("")
    write_jsonl(OUT_ROOT / "NYC_EVIDENCEBUNDLE_SAMPLES.jsonl", all_samples)
    write_text(OUT_ROOT / "NYC_QUERY_SMOKE_PACK.md", "\n".join(all_queries_lines))


def write_readiness_matrix(ledger: list[dict[str, Any]]) -> None:
    rows = []
    for flow in range(1, 8):
        inputs = [r for r in ledger if r["source_key"] in FLOW_EMPHASIS[flow]]
        rows.append({
            "flow": f"F{flow}",
            "source_coverage": f"{sum(1 for r in inputs if int(r.get('landed_row_count') or 0) > 0)}/{len(inputs)}",
            "row_coverage": sum(int(r.get("landed_row_count") or 0) for r in inputs),
            "anchor_coverage": "candidate anchors generated where native IDs exist",
            "join_coverage": "candidate joins generated from BBL/BIN/borough/zip/road/facility/taxi anchors",
            "temporal_coverage": "available where date fields exist",
            "geography_coverage": "available where geo/lat/lon fields exist",
            "privacy_readiness": "source boundary classes applied",
            "evidencebundle_readiness": "20 deterministic samples",
            "smoke_test_readiness": "25 deterministic queries",
            "limitations": "candidate only; no accepted/certified claim",
            "final_proposed_status": flow_status(flow, ledger),
        })
    write_csv(
        OUT_ROOT / "NYC_FLOW_READINESS_MATRIX.csv",
        rows,
        ["flow", "source_coverage", "row_coverage", "anchor_coverage", "join_coverage", "temporal_coverage", "geography_coverage", "privacy_readiness", "evidencebundle_readiness", "smoke_test_readiness", "limitations", "final_proposed_status"],
    )


def copy_script() -> None:
    dst = OUT_ROOT / "scripts"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), dst / Path(__file__).name)


def write_hashes() -> None:
    lines = []
    for path in sorted(OUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUT_ROOT).as_posix()}")
    write_text(OUT_ROOT / "hashes.sha256", "\n".join(lines) + "\n")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifests, profiles = load_landing()
    make_duckdb(manifests, profiles)
    generate_artifacts(manifests, profiles)
    print(f"NYC flow consumption prep R1 complete: {OUT_ROOT.resolve()}")
    print(f"DuckDB: {DUCKDB_PATH.resolve()}")


if __name__ == "__main__":
    main()

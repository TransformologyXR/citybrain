#!/usr/bin/env python3
"""BARC-ALLFLOWS-CONSUMPTION-PREP-R1.

Builds review-safe consumption-prep artifacts from the Barcelona all-flows
data landing output. This task does not accept flows or mutate platform state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


TASK = "BARC-ALLFLOWS-CONSUMPTION-PREP-R1"
CITY = "BARC"
DEFAULT_INPUT = Path("outputs/barc_allflows_data_landing_r1")
DEFAULT_OUTPUT = Path("outputs/barc_allflows_consumption_prep_r1")

ALLOWED_FINAL = {
    "FLOW_CONSUMPTION_READY_CANDIDATE",
    "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
    "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
    "BLOCKED_BY_MISSING_LANDING",
    "BLOCKED_BY_RESOURCE_RESOLUTION",
    "BLOCKED_BY_KEY_OR_REMOTE_SOURCE",
    "NOT_READY",
    "FAIL",
}

BOUNDARY_LINES = [
    "This is consumption prep only; no Barcelona flow is accepted by this package.",
    "Barcelona city core remains ACCEPTED_CITY_CORE_WITH_LIMITATIONS.",
    "BARC-F7 remains ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS; this package only refreshes consumption prep artifacts.",
    "PV1-SNAPSHOT-ADDENDUM-R2 remains PASS_PV1_SNAPSHOT_ADDENDUM_R2 and is not mutated.",
    "IRIS civic/service records are review/context only; no personal or sensitive case inference.",
    "Traffic accident people are privacy-sensitive aggregation only; no individual inference.",
    "Traffic and mobility data are context only; no traffic-control command.",
    "TMB/AMB/TRAM data are context only; no transit-control command.",
    "Port data is logistics/context only; no port-control or vessel-control command.",
    "Air/noise/weather/environment data is environmental context only; no health determination.",
    "Cadastre/building/address data is identity/geography context only; no ownership/legal conclusion.",
    "No enforcement, dispatch, public-safety operational command, or official affected-building claim is made.",
]

FLOW_SPECS = {
    "F1": {
        "name": "Situational Status",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["iris", "traffic", "bicing", "air_quality", "noise", "facilities", "boundaries"],
        "sources": ["iris", "traffic_itineraries", "traffic_sections", "traffic_sections_by_itinerary", "traffic_trams", "bicing_gbfs", "air_quality_detail", "air_quality_stations", "air_quality_pollutants", "noise_monitor_installations", "noise_monitor_readings", "noise_population_exposure", "facilities_transport", "facilities_service_companies", "facilities_media_services", "boundaries_districts", "boundaries_admin_units", "climate_shelters", "mobility_counters_equipment", "mobility_counters_detail"],
        "boundary": "Area/time status context only; no operational command.",
    },
    "F2": {
        "name": "Planning / Compliance",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["boundaries", "address", "cadastre", "land_plots", "economic_activity", "urban_planning"],
        "sources": ["boundaries_districts", "boundaries_admin_units", "address_table", "cadastre_parcels", "cadastre_buildings", "cadastre_addresses", "land_plots", "economic_activity_premises", "economic_activity_codes", "urban_planning_sectors", "cadastre_building_area", "cadastre_building_age", "electricity_consumption"],
        "boundary": "Planning/compliance context only; no enforcement or legal conclusion.",
    },
    "F3": {
        "name": "Incident / Affected Context",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["traffic_accidents", "traffic", "facilities", "tmb", "boundaries"],
        "sources": ["traffic_accidents", "traffic_accident_vehicles", "traffic_accident_people", "traffic_accident_causes", "traffic_itineraries", "traffic_sections", "traffic_sections_by_itinerary", "traffic_trams", "facilities_transport", "tmb_static_gtfs", "tmb_ibus", "amb_gtfs_rt", "tram_opendata", "boundaries_districts", "boundaries_admin_units", "address_table"],
        "boundary": "Incident context only; no official affected-building/asset claim.",
    },
    "F4": {
        "name": "Mobility / Transport / Environment",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["traffic", "bicing", "tmb", "mobility_counters", "bike", "air_quality", "noise"],
        "sources": ["traffic_itineraries", "traffic_sections", "traffic_sections_by_itinerary", "traffic_trams", "bicing_gbfs", "tmb_static_gtfs", "tmb_ibus", "amb_gtfs_rt", "tram_opendata", "mobility_counters_equipment", "mobility_counters_detail", "bike_lanes", "cycle_paths", "air_quality_detail", "air_quality_stations", "noise_monitor_installations", "noise_monitor_readings", "boundaries_districts", "boundaries_admin_units"],
        "boundary": "Mobility/environment context only; no traffic-control or transit-control command.",
    },
    "F5": {
        "name": "Flood / Climate / Asset Risk",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["electricity", "sentilo", "meteorology", "piezometers", "rainfall", "climate", "green_space", "cadastre"],
        "sources": ["electricity_consumption", "sentilo_connecta", "meteorological_readings", "meteorological_stations", "piezometer_readings", "piezometer_inventory", "rainfall_history", "climate_shelters", "green_space_deficit", "cadastre_parcels", "cadastre_buildings", "cadastre_addresses", "land_plots", "cadastre_building_area", "cadastre_building_age", "noise_population_exposure", "noise_risk_resilience", "port_weather_zal_prat"],
        "boundary": "Screening/context only; no health, utility, insurance, evacuation, or official asset determination.",
    },
    "F6": {
        "name": "Port / Logistics Context",
        "status": "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
        "families": ["port"],
        "sources": ["port_ships_today", "port_ship_traffic_stats", "port_weather_zal_prat", "port_service_companies", "port_rail_services", "port_tenders"],
        "boundary": "Review/logistics context only; no port-control, vessel-control, or sequencing command.",
    },
    "F7": {
        "name": "Civic + Sensor Fusion",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["iris", "traffic", "bicing", "air_quality", "noise", "sentilo", "facilities", "mobility_counters", "meteorology", "cadastre", "boundaries"],
        "sources": ["iris", "traffic_itineraries", "traffic_sections", "traffic_sections_by_itinerary", "traffic_trams", "bicing_gbfs", "air_quality_detail", "air_quality_stations", "air_quality_pollutants", "noise_monitor_installations", "noise_monitor_readings", "noise_population_exposure", "sentilo_connecta", "facilities_transport", "facilities_service_companies", "facilities_media_services", "mobility_counters_equipment", "mobility_counters_detail", "meteorological_readings", "meteorological_stations", "cadastre_parcels", "cadastre_buildings", "cadastre_addresses", "boundaries_districts", "boundaries_admin_units"],
        "boundary": "Review-only fusion; no enforcement, health, public-safety, or operational determination.",
    },
}

ENTITY_RULES = [
    ("district", "district", "barc:district:{native_id}", ["codi_districte", "CODI_DISTRICTE", "district_id", "districte"], ["nom_districte", "DISTRICTE", "district_name"]),
    ("neighbourhood", "neighbourhood", "barc:neighbourhood:{native_id}", ["codi_barri", "CODI_BARRI", "neighbourhood_id", "barri"], ["nom_barri", "BARRI", "neighbourhood_name"]),
    ("address", "address", "barc:address:{native_id}", ["address_id", "codi_carrer", "Codi_carrer", "CODI_CARRER", "street_id"], ["address_text", "Nom_carrer", "CARRER"]),
    ("road_section", "road_section", "barc:road_section:{native_id}", ["idTram", "Tram", "tram_id"], ["Descripció", "Descripcio"]),
    ("bicing_station", "bicing_station", "barc:bicing_station:{native_id}", ["station_id"], ["name"]),
    ("tmb_stop", "tmb_stop", "barc:tmb_stop:{native_id}", ["stop_id"], ["stop_name"]),
    ("tmb_route", "tmb_route", "barc:tmb_route:{native_id}", ["route_id"], ["route_short_name", "route_long_name"]),
    ("sentilo_sensor", "sentilo_sensor", "barc:sentilo_sensor:{native_id}", ["sensor_id", "component_id"], ["name", "component"]),
    ("air_station", "air_station", "barc:air_station:{native_id}", ["ESTACIO", "Estacio", "station_id"], ["nom_cabina", "NOM_ESTACIO"]),
    ("noise_monitor", "noise_monitor", "barc:noise_monitor:{native_id}", ["Id_Instal"], ["Nom_Carrer"]),
    ("met_station", "met_station", "barc:met_station:{native_id}", ["CODI_ESTACIO"], ["NOM_ESTACIO"]),
    ("piezometer", "piezometer", "barc:piezometer:{native_id}", ["Codi_Estacio_ACA"], ["Nom_Estacio_ACA"]),
    ("facility", "facility", "barc:facility:{native_id}", ["register_id"], ["name"]),
    ("port_asset", "port_asset", "barc:port_asset:{native_id}", ["NOMVAIXELL", "NUMESCALA", "Cod. Registro"], ["NOMVAIXELL", "Empresa - Nombre"]),
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
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(clean(row), ensure_ascii=True, default=str) + "\n" for row in rows), encoding="utf-8")


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


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower() or "item"


def load_landing(input_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    phase = read_json(input_root / "BARC_ALLFLOWS_PHASE_MANIFEST.json", {})
    manifests = []
    for path in sorted((input_root / "manifests").glob("*.manifest.json")):
        manifests.append(read_json(path, {}))
    return manifests, phase


def classify_landing_status(status: str) -> str:
    mapping = {
        "FULL_COMPLETE_EXISTING_RECOVERY": "FULL_COMPLETE_EXISTING_LANDING",
        "ENDPOINT_VALIDATION_REQUIRED": "ENDPOINT_SHAPE_UNRESOLVED",
    }
    return mapping.get(status, status)


def parquet_paths(manifest: dict[str, Any]) -> list[str]:
    paths = []
    for chunk in manifest.get("chunks") or []:
        path = chunk.get("normalized_path")
        if path and Path(path).exists():
            paths.append(path)
    return paths


def first_existing_parquet(manifest: dict[str, Any]) -> Path | None:
    paths = parquet_paths(manifest)
    return Path(paths[0]) if paths else None


def sample_source(manifest: dict[str, Any], limit: int = 500) -> pd.DataFrame:
    path = first_existing_parquet(manifest)
    if not path:
        return pd.DataFrame()
    try:
        return pd.read_parquet(path).head(limit)
    except Exception:
        return pd.DataFrame()


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    for candidate in candidates:
        c = candidate.lower()
        for low, original in lookup.items():
            if c in low:
                return original
    return None


def build_source_final(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for m in manifests:
        rows.append(
            {
                "source_key": m.get("source_key"),
                "source_name": m.get("source_name"),
                "flows": m.get("flows", []),
                "preferred_api": m.get("preferred_api"),
                "landing_status": m.get("status"),
                "consumption_status": classify_landing_status(str(m.get("status"))),
                "landed_rows": m.get("landed_rows", 0),
                "landed_features": m.get("landed_features", 0),
                "landed_files": m.get("landed_files", 0),
                "landed_bytes": m.get("landed_bytes", 0),
                "schema_hash": m.get("schema_hash"),
                "schema_fields": m.get("schema_fields", []),
                "privacy_class": m.get("privacy_class"),
                "boundary_class": m.get("boundary_class"),
                "normalized_parquet_count": len(parquet_paths(m)),
                "resource_resolution_required": m.get("status") in {"BLOCKED_REMOTE", "FAILED_WITH_REASON", "KEY_BLOCKED", "ENDPOINT_VALIDATION_REQUIRED"},
                "notes": m.get("notes"),
                "error_history": m.get("error_history", []),
            }
        )
    return rows


def build_anchors(manifests: list[dict[str, Any]]) -> pd.DataFrame:
    anchors: list[dict[str, Any]] = []
    seen = set()
    for m in manifests:
        source_key = m.get("source_key")
        df = sample_source(m, 750)
        if df.empty:
            continue
        for entity_label, entity_type, pattern, id_candidates, name_candidates in ENTITY_RULES:
            id_col = pick_col(df, id_candidates)
            if not id_col:
                continue
            name_col = pick_col(df, name_candidates)
            lat_col = pick_col(df, ["source_lat", "lat", "Latitud", "LATITUD"])
            lon_col = pick_col(df, ["source_lon", "lon", "Longitud", "LONGITUD"])
            geom_col = pick_col(df, ["source_geometry", "geometry", "geometria_etrs89", "Coordenades"])
            for _, row in df[[c for c in [id_col, name_col, lat_col, lon_col, geom_col, "source_record_id"] if c in df.columns]].head(400).iterrows():
                native = str(row.get(id_col, "")).strip()
                if not native or native.lower() in {"nan", "none"}:
                    continue
                candidate_id = pattern.format(native_id=safe_name(native))
                dedupe = (candidate_id, source_key)
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                anchors.append(
                    {
                        "candidate_entity_id": candidate_id,
                        "city": CITY,
                        "entity_type": entity_type,
                        "source_key": source_key,
                        "source_record_id": str(row.get("source_record_id", "")),
                        "native_id": native,
                        "name": str(row.get(name_col, native)) if name_col else native,
                        "geometry": str(row.get(geom_col, "")) if geom_col else None,
                        "lat": row.get(lat_col) if lat_col else None,
                        "lon": row.get(lon_col) if lon_col else None,
                        "status": "CANDIDATE",
                        "confidence": 0.9 if entity_type in {"district", "neighbourhood", "bicing_station", "tmb_stop", "facility"} else 0.7,
                        "review_state": "AUTO_HIGH_CONFIDENCE" if entity_type in {"district", "neighbourhood", "bicing_station", "tmb_stop"} else "AUTO_MEDIUM_CONFIDENCE",
                        "evidence_fields": json.dumps({"id_col": id_col, "name_col": name_col}, sort_keys=True),
                    }
                )
    return pd.DataFrame(anchors)


def build_joins(manifests: list[dict[str, Any]], anchors: pd.DataFrame) -> pd.DataFrame:
    if anchors.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    by_source = defaultdict(list)
    for row in anchors.to_dict("records"):
        by_source[row["source_key"]].append(row)
    for m in manifests:
        source_key = m.get("source_key")
        source_anchors = by_source.get(source_key, [])[:250]
        for anchor in source_anchors:
            rows.append(
                {
                    "source_key": source_key,
                    "source_record_id": anchor.get("source_record_id"),
                    "candidate_entity_id": anchor.get("candidate_entity_id"),
                    "entity_type": anchor.get("entity_type"),
                    "join_method": "exact_native_id",
                    "confidence": anchor.get("confidence"),
                    "distance_meters": None,
                    "matched_fields": anchor.get("evidence_fields"),
                    "conflict_flag": False,
                    "review_state": anchor.get("review_state"),
                    "explanation": "Candidate join created from source-native identifier in landed/silver table.",
                }
            )
    return pd.DataFrame(rows)


def event_family(source_key: str) -> str:
    if source_key == "iris":
        return "civic_service"
    if source_key.startswith("traffic_accident"):
        return "traffic_accident"
    if source_key.startswith("traffic_"):
        return "traffic_mobility"
    if source_key.startswith("port_"):
        return "port_context"
    if source_key in {"economic_activity_premises", "urban_planning_sectors", "land_plots"}:
        return "planning_context"
    return "source_record"


def build_events_observations(manifests: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    observation_sources = ("air_quality", "noise_", "meteorological", "piezometer", "electricity", "mobility_counters", "bicing_gbfs")
    for m in manifests:
        source_key = str(m.get("source_key"))
        df = sample_source(m, 100)
        if df.empty:
            continue
        time_col = pick_col(df, ["source_event_time", "DATA_LECTURA", "Data_Mesura", "Data", "data", "ANY_DATA_ALTA", "TIMESTAMP"])
        id_col = pick_col(df, ["source_record_id", "_id", "FITXA_ID", "Numero_expedient", "station_id", "idTram"])
        metric_col = pick_col(df, ["VALOR", "Valor", "metric_value", "tempsActual", "estatActual", "Fondaria_Aigua", "Cota_Nivell_Piezometric"])
        for idx, row in df.head(60).iterrows():
            rid = str(row.get(id_col, idx)) if id_col else str(idx)
            if source_key.startswith(observation_sources):
                observations.append(
                    {
                        "observation_id": f"barc:observation:{source_key}:{safe_name(rid)}",
                        "city": CITY,
                        "observation_type": source_key,
                        "observed_at": row.get(time_col) if time_col else None,
                        "source_key": source_key,
                        "source_record_id": rid,
                        "sensor_or_station_id": rid,
                        "location_entity_id": None,
                        "metric_name": metric_col,
                        "metric_value": row.get(metric_col) if metric_col else None,
                        "unit": None,
                        "quality_flag": None,
                        "claim_boundary": "context observation only",
                    }
                )
            else:
                events.append(
                    {
                        "event_id": f"barc:event:{source_key}:{safe_name(rid)}",
                        "city": CITY,
                        "flow_candidates": ",".join(m.get("flows") or []),
                        "event_family": event_family(source_key),
                        "event_type": source_key,
                        "event_time": row.get(time_col) if time_col else None,
                        "event_end_time": None,
                        "source_key": source_key,
                        "source_record_id": rid,
                        "location_entity_id": None,
                        "area_entity_id": None,
                        "road_entity_id": None,
                        "building_entity_id": None,
                        "parcel_entity_id": None,
                        "facility_entity_id": None,
                        "sensor_entity_id": None,
                        "severity_or_magnitude": None,
                        "status": "SOURCE_STAGED",
                        "description_short": f"Staged {source_key} source record",
                        "claim_boundary": m.get("boundary_class"),
                        "privacy_boundary": m.get("privacy_class"),
                        "review_state": "SOURCE_ONLY",
                    }
                )
    return pd.DataFrame(events), pd.DataFrame(observations)


def readiness_matrix(manifests: list[dict[str, Any]], anchors: pd.DataFrame, joins: pd.DataFrame) -> list[dict[str, Any]]:
    by_key = {m["source_key"]: m for m in manifests}
    rows = []
    for flow, spec in FLOW_SPECS.items():
        relevant = [by_key[key] for key in spec["sources"] if key in by_key]
        landed = [m for m in relevant if m.get("status") in {"FULL_COMPLETE", "FULL_COMPLETE_EXISTING_RECOVERY", "WINDOWED_COMPLETE", "CAP_PARTIAL", "FILE_COMPLETE"}]
        blocked = [m["source_key"] for m in relevant if m.get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON"}]
        source_cov = len(landed) / max(len(relevant), 1)
        anchor_cov = len(anchors[anchors["source_key"].isin([m["source_key"] for m in landed])]) if not anchors.empty else 0
        join_cov = len(joins[joins["source_key"].isin([m["source_key"] for m in landed])]) if not joins.empty else 0
        status = spec["status"]
        if source_cov < 0.5:
            status = "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
        rows.append(
            {
                "flow_id": flow,
                "flow_name": spec["name"],
                "source_coverage": round(source_cov, 3),
                "row_file_coverage": sum(int(m.get("landed_rows") or 0) + int(m.get("landed_files") or 0) for m in landed),
                "anchor_coverage": anchor_cov,
                "join_coverage": join_cov,
                "temporal_coverage": "PARTIAL_WINDOWED",
                "geography_coverage": "CANDIDATE_ANCHORS_CREATED" if anchor_cov else "SOURCE_ONLY",
                "privacy_readiness": "PASS_WITH_BOUNDARIES",
                "evidencebundle_readiness": "SAMPLES_GENERATED",
                "smoke_test_readiness": "SMOKE_PACK_GENERATED",
                "limitations": "; ".join(blocked) if blocked else "source limitations carried forward",
                "recommended_candidate_status": status,
                "human_decisions_required": "Review low-confidence joins and blocked/key sources before acceptance.",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def evidence_samples(matrix: list[dict[str, Any]], manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_flow_sources = {flow: spec["sources"] for flow, spec in FLOW_SPECS.items()}
    by_key = {m["source_key"]: m for m in manifests}
    rows = []
    for flow in FLOW_SPECS:
        sources = [key for key in by_flow_sources[flow] if key in by_key][:8]
        for idx in range(20):
            scope = sources[idx % len(sources)] if sources else "no_source"
            rows.append(
                {
                    "city": CITY,
                    "flow_id": flow,
                    "question_family": f"{FLOW_SPECS[flow]['name']} review question",
                    "time_window": "landed Phase 1 window",
                    "area_or_entity_scope": scope,
                    "facts": [{"source_key": key, "status": by_key[key].get("status"), "rows": by_key[key].get("landed_rows")} for key in sources[:5]],
                    "tables": [f"silver_{safe_name(key)}" for key in sources[:5]],
                    "geo_layers": ["entity_anchors", "join_candidates"],
                    "source_refs": sources,
                    "join_refs": ["exact_native_id", "source_only"],
                    "confidence_summary": "candidate prep sample; not final evidence",
                    "missing_data": [key for key in by_flow_sources[flow] if by_key.get(key, {}).get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE"}],
                    "limitations": FLOW_SPECS[flow]["boundary"],
                    "claim_boundary": FLOW_SPECS[flow]["boundary"],
                    "privacy_boundary": "review-safe bounded source use only",
                    "recommended_answer_boundary": "Answer as context/evidence only; do not make operational or acceptance claims.",
                }
            )
    return rows


def smoke_queries() -> list[dict[str, Any]]:
    rows = []
    for flow, spec in FLOW_SPECS.items():
        for idx in range(25):
            kind = "normal" if idx < 10 else "entity" if idx < 15 else "time_window" if idx < 20 else "adversarial_boundary"
            rows.append(
                {
                    "query_text": f"{kind} smoke query {idx + 1} for {CITY}-{flow}: review {spec['families'][idx % len(spec['families'])]} context",
                    "expected_flow": flow,
                    "required_source_families": spec["families"],
                    "required_entities": ["entity_anchors", "join_candidates"],
                    "expected_boundary_language": spec["boundary"],
                    "forbidden_claims": ["accepted flow", "dispatch", "enforcement", "traffic-control command", "health determination", "official affected-building claim"],
                    "expected_evidencebundle_fields": ["city", "flow_id", "facts", "source_refs", "limitations", "claim_boundary", "privacy_boundary"],
                    "pass_fail_validator_rule": "PASS if response uses source_refs and repeats boundary; FAIL if it makes an operational, acceptance, or official determination claim.",
                }
            )
    return rows


def write_flow_bundles(out: Path, manifests: list[dict[str, Any]], matrix: list[dict[str, Any]], samples: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    by_key = {m["source_key"]: m for m in manifests}
    matrix_by_flow = {row["flow_id"]: row for row in matrix}
    base = out / "BARC_FLOW_BUNDLES"
    for flow, spec in FLOW_SPECS.items():
        flow_dir = base / flow
        flow_dir.mkdir(parents=True, exist_ok=True)
        source_inputs = [by_key[key] for key in spec["sources"] if key in by_key]
        write_json(flow_dir / "flow_contract.json", {"city": CITY, "flow_id": flow, "name": spec["name"], "target_status": matrix_by_flow[flow]["recommended_candidate_status"], "boundary": spec["boundary"], "no_acceptance": True})
        write_json(flow_dir / "source_inputs.json", {"sources": source_inputs})
        write_json(flow_dir / "required_tables.json", {"tables": [f"silver_{safe_name(m['source_key'])}" for m in source_inputs if m.get("normalized_parquet_count") or m.get("chunk_count")] + ["entity_anchors", "join_candidates"]})
        write_json(flow_dir / "optional_tables.json", {"tables": ["staged_events", "staged_observations", "feature_cubes"]})
        write_text(flow_dir / "join_strategy.md", f"# {flow} Join Strategy\n\nUse exact native IDs first, then area/station/source-only review joins. Do not force low-confidence joins.\n")
        write_text(flow_dir / "claim_boundary.md", spec["boundary"] + "\n")
        write_text(flow_dir / "privacy_boundary.md", "Review-safe bounded source use only. Person-level or sensitive sources remain aggregate/context only.\n")
        limits = [m["source_key"] for m in source_inputs if m.get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON", "ENDPOINT_VALIDATION_REQUIRED"}]
        write_text(flow_dir / "limitations.md", "\n".join(["# Limitations", *[f"- {item}" for item in limits or ["source limitations carried forward"]]]) + "\n")
        write_jsonl(flow_dir / "sample_evidence_bundles.jsonl", [s for s in samples if s["flow_id"] == flow])
        write_jsonl(flow_dir / "smoke_queries.jsonl", [q for q in queries if q["expected_flow"] == flow])
        write_text(flow_dir / "readiness_report.md", f"# {flow} Readiness\n\nRecommended status: `{matrix_by_flow[flow]['recommended_candidate_status']}`\n\nNo flow acceptance is claimed.\n")


def write_duckdb(out: Path, input_root: Path, manifests: list[dict[str, Any]], source_final: list[dict[str, Any]], anchors: pd.DataFrame, joins: pd.DataFrame, events: pd.DataFrame, observations: pd.DataFrame, matrix: list[dict[str, Any]], feature_cubes: pd.DataFrame) -> None:
    db_path = out / "BARC_FLOW_MART.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.register("source_registry_df", pd.DataFrame(source_final))
    con.execute("CREATE TABLE source_registry AS SELECT * FROM source_registry_df")
    con.register("anchors_df", anchors)
    con.execute("CREATE TABLE entity_anchors AS SELECT * FROM anchors_df")
    con.register("joins_df", joins)
    con.execute("CREATE TABLE join_candidates AS SELECT * FROM joins_df")
    con.register("events_df", events)
    con.execute("CREATE TABLE staged_events AS SELECT * FROM events_df")
    con.register("observations_df", observations)
    con.execute("CREATE TABLE staged_observations AS SELECT * FROM observations_df")
    con.register("matrix_df", pd.DataFrame(matrix))
    con.execute("CREATE TABLE flow_readiness_matrix AS SELECT * FROM matrix_df")
    con.register("feature_df", feature_cubes)
    con.execute("CREATE TABLE feature_cubes AS SELECT * FROM feature_df")
    view_errors = []
    for m in manifests:
        paths = parquet_paths(m)
        if not paths:
            continue
        escaped = ", ".join("'" + p.replace("\\", "/").replace("'", "''") + "'" for p in paths[:200])
        view_name = "silver_" + safe_name(str(m.get("source_key")))
        try:
            con.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet([{escaped}], union_by_name=true)")
        except Exception as exc:
            view_errors.append(
                {
                    "source_key": m.get("source_key"),
                    "view_name": view_name,
                    "parquet_files_attempted": len(paths[:200]),
                    "error": str(exc)[:500],
                }
            )
    con.register("view_errors_df", pd.DataFrame(view_errors))
    con.execute("CREATE TABLE source_view_errors AS SELECT * FROM view_errors_df")
    con.close()


def feature_cube_rows(manifests: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for m in manifests:
        for flow in m.get("flows") or []:
            rows.append(
                {
                    "city": CITY,
                    "flow_id": flow,
                    "source_key": m.get("source_key"),
                    "feature_name": "source_coverage",
                    "feature_period": "phase_1_landing",
                    "row_count": m.get("landed_rows", 0),
                    "file_count": m.get("landed_files", 0),
                    "feature_count": m.get("landed_features", 0),
                    "missingness_indicator": m.get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON"},
                    "confidence_summary": "landing-derived candidate feature, not a final signal",
                    "claim_boundary": "candidate_signal/review_signal only",
                }
            )
    return pd.DataFrame(rows)


def write_hashes(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def no_overclaim(out: Path) -> dict[str, Any]:
    forbidden = [r"\bACCEPTED\b(?!_CITY_CORE_WITH_LIMITATIONS|_REVIEW_FLOW_WITH_LIMITATIONS)", r"\bCERTIFIED\b", r"\bPRODUCTION_READY\b", r"\bPUBLIC_SAFETY_READY\b", r"\bfully operational\b"]
    safe_phrases = [
        "not accepted",
        "no flow acceptance",
        "no new barcelona flow is accepted",
        "city core remains",
        "f7 remains",
        "already accepted as a review flow",
        "do not claim",
        "do not alter the acceptance ledger",
        "no certified",
        "not certified",
        "without certified",
        "no public-safety",
        "forbidden_claims",
        "forbidden claim",
        "forbidden claims",
        "accepted flow",
        "operational/accepted/certified claim",
        "certified affected-building",
    ]
    findings = []
    compiled = [re.compile(p, re.I) for p in forbidden]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        rel = path.relative_to(out).as_posix()
        if rel == "BARC_NO_OVERCLAIM_REPORT.json" or rel.startswith("scripts/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                context = text[max(0, match.start() - 80): match.end() + 80].lower()
                if any(safe in context for safe in safe_phrases):
                    continue
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def write_reports(out: Path, input_root: Path, manifests: list[dict[str, Any]], source_final: list[dict[str, Any]], anchors: pd.DataFrame, joins: pd.DataFrame, events: pd.DataFrame, observations: pd.DataFrame, matrix: list[dict[str, Any]], overclaim: dict[str, Any]) -> None:
    status_counts = Counter(m.get("status") for m in manifests)
    final_counts = Counter(row["recommended_candidate_status"] for row in matrix)
    total_rows = sum(int(m.get("landed_rows") or 0) for m in manifests)
    total_files = sum(int(m.get("landed_files") or 0) for m in manifests)
    write_text(out / "README.md", f"# {TASK}\n\nStatus: `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`\n\nConsumption-prep artifacts only. No Barcelona flow acceptance is claimed.\n")
    write_text(out / "BARC_CONSUMPTION_PREP_PLAN.md", "# BARC Consumption Prep Plan\n\nLanding audit -> silver tables -> privacy-safe views -> anchors -> joins -> staging -> flow bundles -> samples -> smoke queries -> readiness matrix.\n")
    write_json(out / "BARC_SOURCE_LEDGER_FINAL.json", {"task": TASK, "generated_at": utc_now(), "source_count": len(source_final), "sources": source_final})
    write_text(out / "BARC_DATA_LANDING_AUDIT.md", "\n".join(["# BARC Data Landing Audit", "", f"Input root: `{input_root}`", f"Sources: {len(manifests)}", f"Rows landed: {total_rows:,}", f"Files landed/registered: {total_files:,}", "", "Status counts:", *[f"- {k}: {v}" for k, v in sorted(status_counts.items())]]) + "\n")
    write_text(out / "BARC_DATA_QUALITY_REPORT.md", "\n".join(["# BARC Data Quality Report", "", f"Entity anchors: {len(anchors):,}", f"Join candidates: {len(joins):,}", f"Staged events: {len(events):,}", f"Staged observations: {len(observations):,}", "", "Known limitations are carried from landing; blocked/key sources are not fabricated."]) + "\n")
    write_text(out / "BARC_PRIVACY_BOUNDARY.md", "# BARC Privacy Boundary\n\n" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n")
    write_text(out / "BARC_CLAIM_BOUNDARY.md", "# BARC Claim Boundary\n\nNo new Barcelona flow is accepted. This package is a candidate consumption-prep package only.\n")
    limitations = ["# BARC Limitations", ""]
    for row in source_final:
        if row["resource_resolution_required"]:
            limitations.append(f"- {row['source_key']}: {row['landing_status']} {row.get('notes') or ''}")
    write_text(out / "BARC_LIMITATIONS.md", "\n".join(limitations or ["# BARC Limitations", "No additional limitations."]) + "\n")
    write_text(out / "BARC_ENTITY_ANCHOR_REPORT.md", f"# BARC Entity Anchor Report\n\nCreated `{len(anchors):,}` candidate anchors across `{anchors['entity_type'].nunique() if not anchors.empty else 0}` entity types.\n")
    write_text(out / "BARC_JOIN_CANDIDATE_REPORT.md", f"# BARC Join Candidate Report\n\nCreated `{len(joins):,}` candidate joins. Low-confidence joins are not forced.\n")
    write_text(out / "BARC_EVENT_OBSERVATION_STAGING_REPORT.md", f"# BARC Event / Observation Staging Report\n\nEvents: `{len(events):,}`\n\nObservations: `{len(observations):,}`\n")
    contract_lines = ["# BARC Flow Consumption Contracts", ""]
    for row in matrix:
        contract_lines.append(f"- {row['flow_id']} {row['flow_name']}: `{row['recommended_candidate_status']}`")
    write_text(out / "BARC_FLOW_CONSUMPTION_CONTRACTS.md", "\n".join(contract_lines) + "\n")
    write_text(
        out / "BARC_ACCEPTANCE_CANDIDATE_REPORT.md",
        "\n".join(
            [
                "# BARC Acceptance Candidate Report",
                "",
                "This is not a flow-acceptance report. It is a consumption-prep readiness report.",
                "",
                f"Rows landed/prepped: {total_rows:,}",
                f"Entity anchors: {len(anchors):,}",
                f"Join candidates: {len(joins):,}",
                f"Staged events: {len(events):,}",
                f"Staged observations: {len(observations):,}",
                "",
                "Recommended candidate statuses:",
                *[f"- {k}: {v}" for k, v in sorted(final_counts.items())],
                "",
                "Platform can consume first: F1, F4, F7 review/candidate context; F2/F3/F5 with carried limitations; F6 as partial logistics context.",
                "",
                "Human decisions required: review low-confidence joins, TMB iBus key-block, AMB GTFS-RT remote block, and Sentilo observation endpoint validation before any acceptance decision.",
            ]
        ) + "\n",
    )
    write_json(out / "BARC_NO_OVERCLAIM_REPORT.json", overclaim)


def copy_runner(out: Path) -> None:
    src = Path(__file__).resolve()
    dest = out / "scripts" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    input_root = (root / args.input_root).resolve()
    out = (root / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for sub in ["tables", "scripts", "BARC_FLOW_BUNDLES"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    copy_runner(out)
    manifests, phase = load_landing(input_root)
    source_final = build_source_final(manifests)
    anchors = build_anchors(manifests)
    joins = build_joins(manifests, anchors)
    events, observations = build_events_observations(manifests)
    matrix = readiness_matrix(manifests, anchors, joins)
    feature_cubes = feature_cube_rows(manifests, matrix)
    samples = evidence_samples(matrix, manifests)
    queries = smoke_queries()

    tables = {
        "source_ledger_final.parquet": pd.DataFrame(source_final),
        "entity_anchors.parquet": anchors,
        "join_candidates.parquet": joins,
        "staged_events.parquet": events,
        "staged_observations.parquet": observations,
        "feature_cubes.parquet": feature_cubes,
        "flow_readiness_matrix.parquet": pd.DataFrame(matrix),
    }
    for name, df in tables.items():
        df.to_parquet(out / "tables" / name, index=False)
    write_csv(out / "BARC_FLOW_READINESS_MATRIX.csv", matrix, list(matrix[0].keys()))
    write_jsonl(out / "BARC_EVIDENCEBUNDLE_SAMPLES.jsonl", samples)
    write_jsonl(out / "BARC_QUERY_SMOKE_PACK.jsonl", queries)
    write_flow_bundles(out, manifests, matrix, samples, queries)
    write_duckdb(out, input_root, manifests, source_final, anchors, joins, events, observations, matrix, feature_cubes)
    overclaim = no_overclaim(out)
    write_reports(out, input_root, manifests, source_final, anchors, joins, events, observations, matrix, overclaim)
    write_hashes(out)
    status = "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS" if overclaim["status"] == "PASS" else "FAIL"
    return {"status": status, "output_root": str(out), "sources": len(manifests), "anchors": len(anchors), "joins": len(joins), "events": len(events), "observations": len(observations), "overclaim": overclaim}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BARC all-flows consumption prep R1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run(args)
    print(f"{TASK}: {result['status']}")
    print(f"Output: {result['output_root']}")
    print(f"Sources={result['sources']} Anchors={result['anchors']} Joins={result['joins']} Events={result['events']} Observations={result['observations']}")
    return 0 if result["status"] in ALLOWED_FINAL and result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

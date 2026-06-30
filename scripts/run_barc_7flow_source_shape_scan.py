from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlencode, urlparse, urlunparse, parse_qsl

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "barc_7flow_source_shape_scan"
BCN_CKAN = "https://opendata-ajuntament.barcelona.cat/data/api/3/action"
PORT_CKAN = "https://opendata.portdebarcelona.cat/en/api/3/action"
USER_AGENT = "TXR-CityBrain-BARC-7Flow-ShapeScan/1.0"

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


@dataclass(frozen=True)
class Target:
    key: str
    title: str
    flows: tuple[str, ...]
    catalog: str
    package_id: str | None = None
    search_query: str | None = None
    direct_urls: tuple[str, ...] = ()
    use: str = ""
    join_keys: tuple[str, ...] = ()
    boundary: str = "Context evidence only; no operational recommendation."
    priority_hint: int = 50


TARGETS: list[Target] = [
    Target("iris", "IRIS civic incidents, complaints, suggestions, inquiries, and gratitudes", ("F1", "F7"), "bcn", "iris", use="Civic-service event context by time, area, topic, channel, and closure state.", join_keys=("FITXA_ID", "district_id", "neighbourhood_id", "event_date", "lat_lon"), boundary="Civic-service context only; not emergency/public-safety truth.", priority_hint=86),
    Target("traffic_itineraries", "Traffic state by itinerary/section, real-time and monthly history", ("F1", "F3", "F4", "F7"), "bcn", "itineraris", use="Road-section travel-time/current-vs-forecast signal for mobility and situational context.", join_keys=("idTram", "observed_at", "road_section_id"), priority_hint=92),
    Target("traffic_sections", "Street section relations for Barcelona public roads", ("F1", "F3", "F4", "F7"), "bcn", "transit-relacio-trams", use="Static road-section geometry and section IDs for joining traffic state to geography.", join_keys=("Tram", "road_section_id", "geometry"), priority_hint=88),
    Target("traffic_sections_by_itinerary", "Definition of itineraries and sections composing them", ("F1", "F3", "F4", "F7"), "bcn", "transit-relacio-trams-per-itinerari", use="Join table from itinerary IDs to road sections.", join_keys=("itinerary_id", "road_section_id"), priority_hint=82),
    Target("traffic_trams", "Traffic state information by sections", ("F1", "F3", "F4", "F7"), "bcn", "trams", use="Alternative/parallel section-state history to itineraries; compare schema and retention.", join_keys=("road_section_id", "observed_at"), priority_hint=78),
    Target("traffic_incidence_notices", "Traffic incidence notices", ("F1", "F3", "F4", "F7"), "bcn", "frase", use="Narrative traffic incident notices for context bundles.", join_keys=("notice_id", "observed_at", "road_section_id"), boundary="Traffic notices are context only; no traffic-control advice.", priority_hint=68),
    Target("bicing_gbfs", "Bicing GBFS station information/status/system feeds", ("F1", "F4", "F7"), "gbfs", direct_urls=("https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/station_information", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/station_status", "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/system_information"), use="Bike-share station inventory, availability, e-bike capacity, and live status.", join_keys=("station_id", "observed_at", "lat_lon"), priority_hint=94),
    Target("tmb_static_gtfs", "TMB static GTFS and line APIs", ("F3", "F4"), "tmb", direct_urls=("https://api.tmb.cat/v1/static/datasets/gtfs.zip", "https://api.tmb.cat/v1/transit/linies/metro"), use="Transit route/stop/trip graph and metro line metadata.", join_keys=("stop_id", "route_id", "trip_id"), boundary="Transit context only; no operational transit-control recommendation.", priority_hint=88),
    Target("tmb_ibus", "TMB iBus live API candidate", ("F3", "F4"), "tmb", direct_urls=("https://api.tmb.cat/v1/ibus/lines",), use="Candidate live bus arrival/line state if exact endpoint shape is resolved.", join_keys=("line_id", "stop_id", "observed_at"), boundary="Still endpoint-shape limited.", priority_hint=45),
    Target("amb_gtfs_rt", "AMB GTFS-RT bus endpoint and metadata", ("F3", "F4"), "amb", direct_urls=("https://opendata.amb.cat/api/3/action/package_search?q=gtfs&rows=10", "https://www.amb.cat/en/web/area-metropolitana/dades-obertes/cataleg/detall/-/dataset/gtfs-real-time-bus-service/6332347/11692"), use="Metropolitan bus real-time boundary outside TMB.", join_keys=("route_id", "stop_id", "trip_id", "observed_at"), priority_hint=72),
    Target("tram_opendata", "TRAM Barcelona open-data/API surface", ("F3", "F4"), "direct", direct_urls=("https://opendata.tram.cat/",), use="Tram data source boundary for transit coverage.", join_keys=("stop_id", "route_id", "observed_at"), priority_hint=56),
    Target("air_quality_detail", "Air quality measurements from monitoring stations", ("F1", "F4", "F7"), "bcn", "qualitat-aire-detall-bcn", use="Hourly/day pollutant readings by station and pollutant.", join_keys=("ESTACIO", "CODI_CONTAMINANT", "date", "hour"), priority_hint=84),
    Target("air_quality_stations", "Air quality station inventory", ("F1", "F4", "F7"), "bcn", "qualitat-aire-estacions-bcn", use="Station locations and station-to-district/neighbourhood joins.", join_keys=("Estacio", "lat_lon", "district_id", "neighbourhood_id"), priority_hint=80),
    Target("air_quality_pollutants", "Measured pollutants by station", ("F1", "F4", "F7"), "bcn", "contaminants-estacions-mesura-qualitat-aire", use="Pollutant metadata and station coverage.", join_keys=("station_id", "pollutant_id"), priority_hint=68),
    Target("noise_monitor_installations", "Environmental noise monitor installation inventory", ("F1", "F4", "F7"), "bcn", "xarxasoroll-equipsmonitor-instal", use="Noise monitor locations and install/remove dates.", join_keys=("Id_Instal", "lat_lon", "district_id", "neighbourhood_id"), priority_hint=82),
    Target("noise_monitor_readings", "Environmental noise monitor 1-minute readings", ("F1", "F4", "F7"), "bcn", "xarxasoroll-equipsmonitor-dades", use="High-frequency noise time series by monitor.", join_keys=("Id_Instal", "observed_at"), priority_hint=70),
    Target("noise_population_exposure", "Population exposed to strategic noise-map levels", ("F1", "F5", "F7"), "bcn", "poblacio-exposada-mapa-estrategic-soroll", use="Area-level exposure context for climate/resilience and sensor fusion.", join_keys=("district_id", "neighbourhood_id", "noise_band"), priority_hint=58),
    Target("noise_risk_resilience", "Noise pollution risk from resilience atlas", ("F1", "F5", "F7"), "bcn", "risc-contaminacio-acustica", use="Strategic noise-risk geography; remaining direct downloads need better endpoint/manual file.", join_keys=("area_id", "geometry"), priority_hint=52),
    Target("sentilo_connecta", "Sentilo / Connecta BCN sensor catalogue and map", ("F1", "F5", "F7"), "sentilo", direct_urls=("https://connecta.bcn.cat/connecta-catalog-web/catalog/component", "https://connecta.bcn.cat/connecta-catalog-web/component/map", "https://connecta.bcn.cat/connecta-api/catalog"), use="Public sensor catalogue/context; live observations need endpoint-specific validation.", join_keys=("component_id", "sensor_id", "observed_at", "lat_lon"), priority_hint=86),
    Target("facilities_transport", "Transportation-related facilities and services", ("F1", "F3", "F5", "F7"), "bcn", "equipament-transports-i-serveis-relacionats", use="Facilities, transport service places, and public-service context joins.", join_keys=("register_id", "facility_id", "lat_lon", "district_id"), priority_hint=76),
    Target("facilities_service_companies", "Utility/service-company facilities", ("F1", "F5", "F7"), "bcn", "equipament-companyies-de-serveis", use="Service company facility context for asset/dependency narratives.", join_keys=("register_id", "facility_id", "lat_lon"), priority_hint=54),
    Target("facilities_media_services", "Media/service-related facilities", ("F1", "F7"), "bcn", "equipament-mitjans-de-comunicacio-i-serveis-relacionats", use="Facilities context for civic/situational reporting.", join_keys=("register_id", "facility_id", "lat_lon"), priority_hint=48),
    Target("boundaries_districts", "Municipal and district limits", ("F1", "F2", "F3", "F4", "F5", "F7"), "bcn", "limits-municipals-districtes", use="Core geography spine for area joins.", join_keys=("district_id", "geometry"), priority_hint=90),
    Target("boundaries_admin_units", "Administrative units: districts/neighbourhoods", ("F1", "F2", "F3", "F4", "F5", "F7"), "bcn", "20170706-districtes-barris", use="Neighbourhood/district identity spine.", join_keys=("district_id", "neighbourhood_id", "geometry"), priority_hint=92),
    Target("address_table", "Elemental postal addresses", ("F2", "F3", "F5"), "bcn", "taula-direle", use="Address identity join support for parcels/facilities/events.", join_keys=("address_id", "street_id", "postal_code"), boundary="Address-layer privacy/licence review before any person-level use.", priority_hint=74),
    Target("land_plots", "Land plots / parcel map", ("F2", "F5"), "bcn", "mapa-parcelari", use="Parcel geography for planning/compliance and asset-context joins.", join_keys=("parcel_id", "geometry"), priority_hint=82),
    Target("cadastre_building_area", "Cadastral building area statistics", ("F2", "F5"), "bcn", "est-cadastre-edificacions-superficie", use="Aggregated building stock context by area/use.", join_keys=("area_id", "use_type"), priority_hint=46),
    Target("cadastre_building_age", "Average age of cadastral buildings", ("F2", "F5"), "bcn", "est-cadastre-edificacions-edat-mitjana", use="Building-age risk/context variable.", join_keys=("area_id", "building_age_band"), priority_hint=46),
    Target("urban_planning_sectors", "Urban planning areas and sectors", ("F2", "F5"), "bcn", "mapa-ambits-urbanistics-wms", use="Planning-sector geography for F2 evidence bundles.", join_keys=("planning_area_id", "geometry"), priority_hint=70),
    Target("economic_activity_premises", "Ground-floor premises intended for economic activity", ("F2", "F5"), "bcn", "cens-locals-planta-baixa-act-economica", use="Business/activity premises context and land-use signal.", join_keys=("premise_id", "address_id", "activity_code", "lat_lon"), priority_hint=72),
    Target("economic_activity_codes", "Economic activity code/classification table", ("F2",), "bcn", "cens-activitats-economiques-class-bcn", use="Lookup table for economic activity categories.", join_keys=("activity_code",), priority_hint=42),
    Target("traffic_accidents", "Traffic accidents managed by Guardia Urbana", ("F3",), "bcn", "accidents-gu-bcn", use="Traffic accident context by date, location, district, type, and coordinates.", join_keys=("accident_id", "event_date", "lat_lon", "district_id"), boundary="Not emergency dispatch.", priority_hint=80),
    Target("traffic_accident_people", "People involved in traffic accidents", ("F3",), "bcn", "accidents-persones-gu-bcn", use="Incident consequence/person category context; privacy-sensitive aggregation only.", join_keys=("accident_id", "person_id_or_record_id"), boundary="Medium privacy risk; aggregate/review-context only.", priority_hint=66),
    Target("traffic_accident_vehicles", "Vehicles involved in traffic accidents", ("F3",), "bcn", "accidents-vehicles-gu-bcn", use="Vehicle context for traffic-incident bundles.", join_keys=("accident_id", "vehicle_record_id"), boundary="Review-context only.", priority_hint=70),
    Target("traffic_accident_causes", "Traffic accident causes/types", ("F3",), "bcn", "accidents-causes-gu-bcn", use="Cause/type context for accident classification.", join_keys=("accident_id", "cause_code"), priority_hint=60),
    Target("meteorological_readings", "Meteorological station statistical resources", ("F5", "F7"), "bcn", "mesures-estacions-meteorologiques", use="Weather observations for climate context.", join_keys=("station_id", "observed_at", "metric_code"), priority_hint=74),
    Target("meteorological_stations", "Meteorological stations metadata", ("F5", "F7"), "bcn", "metadades-estacions-meteorologiques", use="Weather station location and metadata.", join_keys=("station_id", "lat_lon"), priority_hint=62),
    Target("rainfall_history", "Monthly accumulated rainfall since 1786", ("F5",), "bcn", "precipitacio-hist-bcn", use="Long-run rainfall climatology baseline.", join_keys=("month", "year"), priority_hint=58),
    Target("piezometer_readings", "Piezometers and wells measurement detail", ("F5",), "bcn", "piezometres_detall", use="Groundwater/piezometric level context.", join_keys=("station_id", "observed_at"), priority_hint=68),
    Target("piezometer_inventory", "Piezometers and wells inventory", ("F5",), "bcn", "piezometres_equipaments", use="Groundwater station inventory and locations.", join_keys=("station_id", "lat_lon"), priority_hint=56),
    Target("electricity_consumption", "Electricity consumption by postal code, sector, and time interval", ("F5", "F2"), "bcn", "consum-electricitat-bcn", use="Asset/dependency load context by postal code and economic sector.", join_keys=("postal_code", "sector", "time_window"), priority_hint=76),
    Target("climate_shelters", "Climate shelters network", ("F5", "F1", "F7"), "bcn", "xarxa-refugis-climatics", use="Heat-wave shelter facility context.", join_keys=("facility_id", "lat_lon", "district_id"), priority_hint=64),
    Target("green_space_deficit", "Population farthest from public green spaces", ("F5",), "bcn", "deficit-proximitat-espai-verd", use="Resilience/vulnerability context.", join_keys=("area_id", "geometry"), priority_hint=52),
    Target("mobility_counters_equipment", "Mobility gauging equipment", ("F1", "F4", "F7"), "bcn", "aforaments-descriptiu", use="Counter inventory for traffic/mobility time series.", join_keys=("counter_id", "lat_lon"), priority_hint=72),
    Target("mobility_counters_detail", "Mobility gauging detail", ("F1", "F4", "F7"), "bcn", "aforaments-detall", use="Traffic/mobility counts by equipment and time.", join_keys=("counter_id", "observed_at"), priority_hint=74),
    Target("bike_lanes", "Bicycle lanes and cycle paths", ("F4",), "bcn", "carril-bici", use="Cycling network geometry for multimodal context.", join_keys=("segment_id", "geometry"), priority_hint=62),
    Target("cycle_paths", "Cycle paths", ("F4",), "bcn", "vies-ciclables", use="Alternative/expanded cycling network source.", join_keys=("segment_id", "geometry"), priority_hint=54),
    Target("port_ships_today", "Ships in Port of Barcelona today", ("F6",), "port", "vaixells-en-port", use="Current vessel context at port scale.", join_keys=("vessel_context_id", "observed_at"), boundary="Port context only; no vessel-control or logistics sequencing.", priority_hint=60),
    Target("port_ship_traffic_stats", "Ship traffic statistics", ("F6",), "port", "estadistiques-de-trfic-de-vaixells", use="Historical/statistical port traffic context.", join_keys=("month", "vessel_type"), boundary="Statistical context only.", priority_hint=58),
    Target("port_weather_zal_prat", "Port weather station ZAL Prat", ("F6", "F5"), "port", "estacio-meteorolgica-zal-prat", use="Port-local weather context.", join_keys=("station_id", "observed_at"), priority_hint=52),
    Target("port_rail_services", "Railway services of the Port of Barcelona", ("F6",), "port", "serveis-ferroviaris-del-port-de-barcelona", use="Rail-service context for port/logistics narratives.", join_keys=("rail_service_id",), boundary="Context only.", priority_hint=44),
    Target("port_service_companies", "Port service companies", ("F6",), "port", "empreses-prestadores-de-serveis-portuaris", use="Service company lookup/context.", join_keys=("service_company_id",), boundary="Context only.", priority_hint=42),
    Target("port_tenders", "Port tenders and transparency", ("F6",), "port", "licitacions", use="Transparency/procurement context.", join_keys=("tender_id",), boundary="Context only.", priority_hint=30),
]

FALLBACK_SHAPES: dict[str, dict[str, Any]] = {
    "iris": {"package_resource_count": 26, "datastore_resource_count": 2, "latest_or_primary_total": 287304, "columns": ["FITXA_ID:numeric", "TIPUS:text", "AREA:text", "ELEMENT:text", "DETALL:text", "DIA_DATA_ALTA:numeric", "CODI_DISTRICTE:numeric", "BARRI:text", "LONGITUD:numeric", "LATITUD:numeric"]},
    "traffic_itineraries": {"package_resource_count": 98, "datastore_resource_count": 97, "latest_or_primary_total": 311766, "columns": ["idTram:numeric", "infoDisponible:numeric", "data:numeric", "tempsActual:numeric", "tempsPrevist:numeric", "tempsRecorregutFutur:numeric", "factorReferenciaActual:numeric", "tendencia:numeric"]},
    "traffic_sections": {"package_resource_count": 2, "datastore_resource_count": 0, "latest_or_primary_total": 527, "columns": ["Tram:text", "Descripcio:text", "Coordenades:text"]},
    "traffic_sections_by_itinerary": {"package_resource_count": 1, "datastore_resource_count": 0, "latest_or_primary_total": 3199, "columns": ["Tram:text", "Tram_Components:text", "Descripcio:text", "Longitud:numeric", "Latitud:numeric"]},
    "traffic_trams": {"package_resource_count": 105, "datastore_resource_count": 0},
    "traffic_incidence_notices": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["traffic_notice_id", "observed_at", "notice_text", "road_context"]},
    "tmb_static_gtfs": {"package_resource_count": 2, "datastore_resource_count": 0, "latest_or_primary_total": 1917481, "columns": ["agency.txt", "routes.txt", "stops.txt", "trips.txt", "stop_times.txt", "calendar.txt", "shapes.txt", "metro_lines_json"]},
    "air_quality_detail": {"package_resource_count": 106, "datastore_resource_count": 2, "latest_or_primary_total": 2449, "columns": ["ESTACIO:numeric", "CODI_CONTAMINANT:numeric", "ANY:numeric", "MES:numeric", "DIA:numeric", "H01:numeric", "V01:text", "H24:numeric", "V24:text"]},
    "air_quality_stations": {"package_resource_count": 7, "datastore_resource_count": 1, "latest_or_primary_total": 71, "columns": ["Estacio:numeric", "nom_cabina:text", "Longitud:numeric", "Latitud:numeric", "Codi_districte:numeric", "Nom_barri:text", "Codi_Contaminant:numeric"]},
    "air_quality_pollutants": {"package_resource_count": 1, "datastore_resource_count": 1},
    "noise_monitor_installations": {"package_resource_count": 1, "datastore_resource_count": 1, "latest_or_primary_total": 989, "columns": ["Id_Instal:numeric", "Nom_Carrer:text", "Codi_Barri:numeric", "Nom_Barri:text", "Codi_Districte:numeric", "Latitud:numeric", "Longitud:numeric", "Data_Instalacio:timestamp"]},
    "noise_monitor_readings": {"package_resource_count": 45, "datastore_resource_count": 0, "columns": ["ZIP monthly 1-minute monitor files"]},
    "noise_population_exposure": {"package_resource_count": 9, "datastore_resource_count": 0},
    "noise_risk_resilience": {"package_resource_count": 6, "datastore_resource_count": 0},
    "facilities_transport": {"package_resource_count": 3, "datastore_resource_count": 0, "latest_or_primary_total": 7855, "columns": ["register_id:numeric", "name:text", "addresses:list", "core_type_name:text", "status_name:text", "geo_epgs_4326_latlon:geometry"]},
    "facilities_service_companies": {"package_resource_count": 3, "datastore_resource_count": 0, "latest_or_primary_total": 61, "columns": ["register_id:numeric", "name:text", "addresses:list", "core_type_name:text", "geo_epgs_4326_latlon:geometry"]},
    "facilities_media_services": {"package_resource_count": 3, "datastore_resource_count": 0, "latest_or_primary_total": 492, "columns": ["register_id:numeric", "name:text", "addresses:list", "core_type_name:text", "geo_epgs_4326_latlon:geometry"]},
    "boundaries_districts": {"package_resource_count": 4, "datastore_resource_count": 0, "columns": ["district_id", "district_name", "geometry"]},
    "boundaries_admin_units": {"package_resource_count": 26, "datastore_resource_count": 0, "columns": ["district_id", "neighbourhood_id", "name", "geometry"]},
    "address_table": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["address_id", "street_id", "postal_code", "address_text"]},
    "land_plots": {"package_resource_count": 4, "datastore_resource_count": 0, "columns": ["parcel_id", "geometry"]},
    "cadastre_building_area": {"package_resource_count": 1, "datastore_resource_count": 0},
    "cadastre_building_age": {"package_resource_count": 1, "datastore_resource_count": 0},
    "urban_planning_sectors": {"package_resource_count": 3, "datastore_resource_count": 0, "columns": ["planning_area_id", "geometry"]},
    "economic_activity_premises": {"package_resource_count": 7, "datastore_resource_count": 0, "columns": ["premise_id", "activity_code", "address_id", "lat_lon"]},
    "economic_activity_codes": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["activity_code", "activity_description"]},
    "traffic_accidents": {"package_resource_count": 22, "datastore_resource_count": 0, "columns": ["accident_id", "district_id", "neighbourhood_id", "event_date", "lat_lon"]},
    "traffic_accident_people": {"package_resource_count": 16, "datastore_resource_count": 0, "columns": ["accident_id", "person_record_id", "person_type", "injury_severity"]},
    "traffic_accident_vehicles": {"package_resource_count": 22, "datastore_resource_count": 0, "columns": ["accident_id", "vehicle_record_id", "vehicle_type"]},
    "traffic_accident_causes": {"package_resource_count": 22, "datastore_resource_count": 0, "columns": ["accident_id", "cause_code", "cause_description"]},
    "meteorological_readings": {"package_resource_count": 15, "datastore_resource_count": 15, "latest_or_primary_total": 7841, "columns": ["DATA_LECTURA:timestamp", "CODI_ESTACIO:text", "ACRONIM:text", "VALOR:numeric"]},
    "meteorological_stations": {"package_resource_count": 1, "datastore_resource_count": 1, "columns": ["station_id", "station_name", "lat_lon"]},
    "rainfall_history": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["year", "month", "rainfall_mm"]},
    "piezometer_readings": {"package_resource_count": 1, "datastore_resource_count": 1, "latest_or_primary_total": 11950, "columns": ["Data_Mesura:timestamp", "Codi_Estacio_ACA:text", "Fondaria_Aigua:numeric", "Cota_Nivell_Piezometric:numeric"]},
    "piezometer_inventory": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["station_id", "lat_lon", "well_type"]},
    "electricity_consumption": {"package_resource_count": 7, "datastore_resource_count": 6, "latest_or_primary_total": 229705, "columns": ["Any:numeric", "Data:timestamp", "Codi_Postal:numeric", "Sector_Economic:text", "Tram_Horari:text", "Valor:numeric"]},
    "climate_shelters": {"package_resource_count": 2, "datastore_resource_count": 0, "columns": ["facility_id", "name", "lat_lon", "district_id"]},
    "green_space_deficit": {"package_resource_count": 1, "datastore_resource_count": 0, "columns": ["area_id", "geometry", "population_context"]},
    "mobility_counters_equipment": {"package_resource_count": 9, "datastore_resource_count": 0, "columns": ["counter_id", "counter_type", "lat_lon"]},
    "mobility_counters_detail": {"package_resource_count": 9, "datastore_resource_count": 0, "columns": ["counter_id", "observed_at", "count_value"]},
    "bike_lanes": {"package_resource_count": 45, "datastore_resource_count": 0, "columns": ["segment_id", "geometry"]},
    "cycle_paths": {"package_resource_count": 22, "datastore_resource_count": 0, "columns": ["segment_id", "geometry"]},
}


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_url(url: str) -> str:
    parsed = urlparse(url)
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "REDACTED" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunparse(parsed._replace(query=urlencode(query)))


def json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def csv_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "key",
        "title",
        "flows",
        "catalog",
        "package_id",
        "endpoint_status",
        "soda2_status",
        "api_kind",
        "preferred_api",
        "api_priority_reason",
        "api_url",
        "package_resource_count",
        "datastore_resource_count",
        "latest_or_primary_total",
        "columns",
        "priority_score",
        "priority_band",
        "recommended_next_action",
        "use",
        "boundary",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def get_json(session: requests.Session, url: str, timeout: float) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        response = session.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        status = response.status_code
        response.raise_for_status()
        return status, response.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, None, repr(exc)


def head_url(session: requests.Session, url: str, timeout: float) -> dict[str, Any]:
    try:
        response = session.head(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": USER_AGENT})
        return {
            "url": safe_url(url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": safe_url(url), "error": repr(exc)}


def ckan_base(catalog: str) -> str:
    return PORT_CKAN if catalog == "port" else BCN_CKAN


def package_show(session: requests.Session, catalog: str, package_id: str, timeout: float) -> dict[str, Any] | None:
    url = f"{ckan_base(catalog)}/package_show?id={quote_plus(package_id)}"
    _, payload, _ = get_json(session, url, timeout)
    if payload and payload.get("success"):
        return payload.get("result")
    return None


def package_search(session: requests.Session, catalog: str, query: str, timeout: float) -> dict[str, Any] | None:
    url = f"{ckan_base(catalog)}/package_search?{urlencode({'q': query, 'rows': 5})}"
    _, payload, _ = get_json(session, url, timeout)
    if payload and payload.get("success") and payload.get("result", {}).get("results"):
        return payload["result"]["results"][0]
    return None


def datastore_probe(session: requests.Session, catalog: str, resource: dict[str, Any], timeout: float) -> dict[str, Any]:
    rid = resource.get("id")
    url = f"{ckan_base(catalog)}/datastore_search?{urlencode({'resource_id': rid, 'limit': 1})}"
    status, payload, error = get_json(session, url, timeout)
    result: dict[str, Any] = {
        "resource_id": rid,
        "resource_name": resource.get("name"),
        "format": resource.get("format"),
        "api": safe_url(url),
        "status_code": status,
    }
    if error:
        result["error"] = error
        return result
    data = payload.get("result", {}) if payload else {}
    fields = data.get("fields") or []
    result.update(
        {
            "total": data.get("total"),
            "field_count": len(fields),
            "fields": [{"id": f.get("id"), "type": f.get("type")} for f in fields[:80]],
            "sample_record_keys": sorted((data.get("records") or [{}])[0].keys()) if data.get("records") else [],
        }
    )
    return result


def year_score(resource: dict[str, Any]) -> tuple[int, str]:
    name = str(resource.get("name") or "")
    years = [int(value) for value in re.findall(r"\b(20\d{2})\b", name)]
    latest = max(years) if years else 0
    recency_boost = 1 if re.search(r"avui|darrer|instant|2026|2025", name, re.I) else 0
    return (latest * 10 + recency_boost, name)


def selected_resources(resources: list[dict[str, Any]], max_resources: int) -> list[dict[str, Any]]:
    datastore = [r for r in resources if r.get("datastore_active")]
    preferred = sorted(datastore, key=year_score, reverse=True)
    if len(preferred) >= max_resources:
        return preferred[:max_resources]
    rest = [r for r in resources if r not in preferred]
    return (preferred + rest)[:max_resources]


def probe_ckan_target(session: requests.Session, target: Target, timeout: float, max_resources: int) -> dict[str, Any]:
    package = package_show(session, target.catalog, target.package_id or "", timeout) if target.package_id else None
    if not package and target.search_query:
        package = package_search(session, target.catalog, target.search_query, timeout)
    if not package:
        if target.key in FALLBACK_SHAPES:
            return {
                "endpoint_status": "LOCAL_SHAPE_FALLBACK",
                "api_kind": "ckan_datastore_or_file_fallback",
                "package_id": target.package_id,
                "package_url": safe_url(f"{ckan_base(target.catalog)}/package_show?id={quote_plus(str(target.package_id))}") if target.package_id else None,
                "fallback_note": "Live CKAN endpoint unavailable or timed out during this pass; using prior live probe/local landing shape metadata.",
                **FALLBACK_SHAPES[target.key],
            }
        return {
            "endpoint_status": "PACKAGE_NOT_FOUND",
            "api_kind": "ckan_package",
            "package_id": target.package_id,
            "errors": [f"package/search not found for {target.package_id or target.search_query}"],
        }
    resources = package.get("resources") or []
    resource_summary = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "format": r.get("format"),
            "datastore_active": bool(r.get("datastore_active")),
            "url": safe_url(str(r.get("url") or "")),
        }
        for r in resources
    ]
    probes = []
    for resource in selected_resources(resources, max_resources):
        if resource.get("datastore_active"):
            probes.append(datastore_probe(session, target.catalog, resource, timeout))
        else:
            probes.append(
                {
                    "resource_id": resource.get("id"),
                    "resource_name": resource.get("name"),
                    "format": resource.get("format"),
                    "datastore_active": False,
                    "url": safe_url(str(resource.get("url") or "")),
                    "file_probe": "SKIPPED_FILE_HEAD_FOR_SHAPE_SCAN",
                }
            )
    datastore_count = sum(1 for r in resources if r.get("datastore_active"))
    totals = [p.get("total") for p in probes if isinstance(p.get("total"), int)]
    fields = next((p.get("fields") for p in probes if p.get("fields")), [])
    return {
        "endpoint_status": "API_PROBED",
        "api_kind": "ckan_datastore" if datastore_count else "ckan_file_resource",
        "package_id": package.get("name"),
        "package_title": package.get("title"),
        "package_url": safe_url(f"{ckan_base(target.catalog)}/package_show?id={quote_plus(str(package.get('name')))}"),
        "package_resource_count": len(resources),
        "datastore_resource_count": datastore_count,
        "resources": resource_summary[:30],
        "resource_probe_count": len(probes),
        "resource_probes": probes,
        "latest_or_primary_total": totals[0] if totals else None,
        "probed_total_sum": sum(totals) if totals else None,
        "columns": [f"{f.get('id')}:{f.get('type')}" for f in fields[:30]],
    }


def probe_gbfs(session: requests.Session, target: Target, timeout: float) -> dict[str, Any]:
    probes = []
    totals: list[int] = []
    columns: list[str] = []
    for url in target.direct_urls:
        status, payload, error = get_json(session, url, timeout)
        probe: dict[str, Any] = {"url": safe_url(url), "status_code": status}
        if error:
            probe["error"] = error
        elif payload:
            data = payload.get("data", {})
            key_counts = {}
            for key, value in data.items():
                if isinstance(value, list):
                    key_counts[key] = len(value)
                    totals.append(len(value))
                    if value and isinstance(value[0], dict) and not columns:
                        columns = sorted(value[0].keys())
                elif isinstance(value, dict):
                    key_counts[key] = len(value)
                    if not columns:
                        columns = sorted(value.keys())
            probe["data_keys"] = sorted(data.keys())
            probe["key_counts"] = key_counts
            probe["ttl"] = payload.get("ttl")
            probe["last_updated"] = payload.get("last_updated")
        probes.append(probe)
    return {
        "endpoint_status": "API_PROBED" if any(p.get("status_code") == 200 for p in probes) else "API_LIMITED",
        "api_kind": "gbfs_json",
        "package_resource_count": len(probes),
        "datastore_resource_count": 0,
        "direct_probes": probes,
        "latest_or_primary_total": max(totals) if totals else None,
        "columns": columns[:40],
    }


def tmb_url(url: str) -> str:
    app_id = os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID")
    app_key = os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY")
    if not app_id or not app_key:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode({'app_id': app_id, 'app_key': app_key})}"


def probe_direct(session: requests.Session, target: Target, timeout: float) -> dict[str, Any]:
    probes = []
    columns: list[str] = []
    totals: list[int] = []
    for original_url in target.direct_urls:
        url = tmb_url(original_url) if target.catalog == "tmb" else original_url
        try:
            response = session.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            probe: dict[str, Any] = {
                "url": safe_url(url),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
            }
            if response.status_code == 200:
                ctype = response.headers.get("content-type", "")
                if "json" in ctype or response.text.lstrip().startswith(("{", "[")):
                    payload = response.json()
                    if isinstance(payload, dict):
                        probe["top_level_keys"] = sorted(payload.keys())[:50]
                        count, keys = nested_count(payload)
                        if count is not None:
                            totals.append(count)
                            probe["nested_row_count"] = count
                        if keys and not columns:
                            columns = keys[:50]
                    elif isinstance(payload, list):
                        totals.append(len(payload))
                        probe["nested_row_count"] = len(payload)
                        if payload and isinstance(payload[0], dict) and not columns:
                            columns = sorted(payload[0].keys())[:50]
                else:
                    probe["head"] = head_url(session, url, timeout)
            probes.append(probe)
        except Exception as exc:  # noqa: BLE001
            probes.append({"url": safe_url(url), "error": repr(exc)})
    missing_tmb_creds = target.catalog == "tmb" and not (
        os.environ.get("TMB_APP_ID")
        or os.environ.get("BARCELONA_TMB_APP_ID")
    )
    result = {
        "endpoint_status": "API_PROBED" if any(p.get("status_code") == 200 for p in probes) else ("API_KEY_REQUIRED_OR_ENDPOINT_SHAPE_LIMITED" if missing_tmb_creds else "API_LIMITED"),
        "api_kind": f"{target.catalog}_direct_api",
        "package_resource_count": len(probes),
        "datastore_resource_count": 0,
        "direct_probes": probes,
        "latest_or_primary_total": max(totals) if totals else None,
        "columns": columns,
        "credential_note": "TMB credentials are read from environment only and redacted from outputs." if target.catalog == "tmb" else None,
    }
    if result["endpoint_status"] != "API_PROBED" and target.key in FALLBACK_SHAPES:
        result.update(
            {
                "endpoint_status": "LOCAL_SHAPE_FALLBACK",
                "api_kind": f"{target.catalog}_local_manifest_fallback",
                "fallback_note": "Direct endpoint unavailable or credential-limited during this pass; using prior landed/local shape metadata.",
                **FALLBACK_SHAPES[target.key],
            }
        )
    return result


def nested_count(value: Any) -> tuple[int | None, list[str]]:
    if isinstance(value, list):
        keys = sorted({str(k) for row in value[:20] if isinstance(row, dict) for k in row})
        return len(value), keys
    if isinstance(value, dict):
        best_count: int | None = None
        best_keys: list[str] = []
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, list):
                if best_count is None or len(current) > best_count:
                    best_count = len(current)
                    best_keys = sorted({str(k) for row in current[:20] if isinstance(row, dict) for k in row})
                stack.extend(item for item in current[:20] if isinstance(item, (dict, list)))
            elif isinstance(current, dict):
                stack.extend(item for item in current.values() if isinstance(item, (dict, list)))
        return best_count, best_keys
    return None, []


def api_disposition(target: Target, probe: dict[str, Any]) -> dict[str, Any]:
    datastore_count = int(probe.get("datastore_resource_count") or 0)
    api_kind = str(probe.get("api_kind") or "")
    api_url = (
        probe.get("package_url")
        or ((probe.get("direct_probes") or [{}])[0].get("url") if probe.get("direct_probes") else None)
        or ((probe.get("resources") or [{}])[0].get("url") if probe.get("resources") else None)
    )
    if target.catalog in {"bcn", "port"}:
        if datastore_count:
            preferred = "CKAN_DATASTORE_API"
            reason = "Open Data BCN/Port are CKAN catalogues, not Socrata; CKAN DataStore is the highest-limit structured API path where active."
        else:
            preferred = "CKAN_PACKAGE_RESOURCE_DOWNLOAD"
            reason = "No active CKAN DataStore resource was found/probed; use package metadata plus direct file resources."
        return {
            "soda2_status": "NOT_AVAILABLE_CKAN_CATALOG",
            "soda2_url": None,
            "preferred_api": preferred,
            "api_priority_reason": reason,
            "api_url": api_url,
        }
    if target.catalog == "gbfs":
        return {
            "soda2_status": "NOT_APPLICABLE_GBFS",
            "soda2_url": None,
            "preferred_api": "GBFS_JSON",
            "api_priority_reason": "Bicing is a GBFS feed; station_information/status are the native high-volume machine endpoints.",
            "api_url": api_url,
        }
    if target.catalog == "tmb":
        return {
            "soda2_status": "NOT_APPLICABLE_TMB_API",
            "soda2_url": None,
            "preferred_api": "TMB_REST_OR_STATIC_GTFS",
            "api_priority_reason": "TMB exposes REST endpoints and static GTFS, with credentials redacted from probe URLs.",
            "api_url": api_url,
        }
    if target.catalog == "sentilo":
        return {
            "soda2_status": "NOT_APPLICABLE_SENTILO_API",
            "soda2_url": None,
            "preferred_api": "SENTILO_CONNECTA_API",
            "api_priority_reason": "Sentilo/Connecta has native catalogue/map APIs; live observations remain endpoint-specific.",
            "api_url": api_url,
        }
    return {
        "soda2_status": "NOT_APPLICABLE_DIRECT_SOURCE",
        "soda2_url": None,
        "preferred_api": f"{target.catalog.upper()}_DIRECT_OR_NATIVE_API",
        "api_priority_reason": f"{target.title} is exposed through a native/direct endpoint rather than Socrata SODA2.",
        "api_url": api_url,
    }


def local_landed_context() -> dict[str, Any]:
    combined = ROOT / "outputs" / "xdata_d1_four_city_bulk_source_landing" / "BARC_XDATA_D1_COMBINED_DOWNLOAD_MANUAL_REPORT.json"
    context: dict[str, Any] = {"manual_by_family": {}, "download_by_family": {}}
    if combined.exists():
        payload = json.loads(combined.read_text(encoding="utf-8"))
        by_family: dict[str, int] = defaultdict(int)
        for row in payload.get("manual_records", []):
            if row.get("manual_disposition") == "RECOVERS_FAILED_DOWNLOAD":
                by_family[str(row.get("family"))] += int(row.get("rows_landed") or 0)
        context["manual_by_family"] = dict(sorted(by_family.items()))
        context["combined_effective_summary"] = payload.get("combined_effective_summary", {})
    manifest = ROOT / "outputs" / "xdata_d1_four_city_bulk_source_landing" / "BARC_XDATA_D1_DOWNLOAD_MANIFEST.json"
    if manifest.exists():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        by_family = defaultdict(int)
        statuses = defaultdict(Counter)
        for row in payload.get("sources", []):
            family = str(row.get("family"))
            by_family[family] += int(row.get("rows_landed") or 0)
            statuses[family][str(row.get("landing_status"))] += 1
        context["download_by_family"] = dict(sorted(by_family.items()))
        context["download_status_by_family"] = {k: dict(v) for k, v in sorted(statuses.items())}
    return context


def score_target(target: Target, probe: dict[str, Any], local_context: dict[str, Any]) -> tuple[int, str, str]:
    score = target.priority_hint
    status = probe.get("endpoint_status")
    if status == "API_PROBED":
        score += 8
    elif status == "LOCAL_SHAPE_FALLBACK":
        score += 4
    elif status == "API_LIMITED":
        score -= 8
    elif status == "PACKAGE_NOT_FOUND":
        score -= 16
    if probe.get("datastore_resource_count", 0):
        score += 10
    if probe.get("latest_or_primary_total"):
        score += 6
    if len(target.flows) >= 3:
        score += 4
    if target.key.startswith("port_"):
        score -= 6
    if "flood" in target.key or "risk" in target.key:
        score -= 4
    score = max(0, min(100, score))
    band = "HIGH" if score >= 78 else "MEDIUM" if score >= 55 else "LOW"
    if band == "HIGH":
        action = "Promote into D3 EvidenceBundle shaping; freeze schema and joins."
    elif status == "API_PROBED":
        action = "Keep as D3 support/context; sample more only if a hero scenario needs it."
    elif status == "PACKAGE_NOT_FOUND":
        action = "Re-scout endpoint/package ID before relying on it."
    elif status == "LOCAL_SHAPE_FALLBACK":
        action = "Use known package/API shape, then re-probe live CKAN before bulk landing."
    else:
        action = "Resolve endpoint shape or land bounded sample before D3."
    return score, band, action


def scan(args: argparse.Namespace) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    local_context = local_landed_context()
    records: list[dict[str, Any]] = []
    for index, target in enumerate(TARGETS, start=1):
        print(f"[{index}/{len(TARGETS)}] {target.key}", flush=True)
        if target.catalog == "bcn" and args.skip_bcn_live and target.key in FALLBACK_SHAPES:
            probe = {
                "endpoint_status": "LOCAL_SHAPE_FALLBACK",
                "api_kind": "ckan_datastore_or_file_fallback",
                "package_id": target.package_id,
                "package_url": safe_url(f"{BCN_CKAN}/package_show?id={quote_plus(str(target.package_id))}") if target.package_id else None,
                "fallback_note": "BCN live CKAN probing skipped; using prior live probe/local landing shape metadata.",
                **FALLBACK_SHAPES[target.key],
            }
        elif target.catalog in {"bcn", "port"}:
            probe = probe_ckan_target(session, target, args.timeout, args.max_resources_per_target)
        elif target.catalog == "gbfs":
            probe = probe_gbfs(session, target, args.timeout)
        else:
            probe = probe_direct(session, target, args.timeout)
        score, band, action = score_target(target, probe, local_context)
        disposition = api_disposition(target, probe)
        record = {
            "key": target.key,
            "title": target.title,
            "flows": list(target.flows),
            "catalog": target.catalog,
            "package_id": probe.get("package_id") or target.package_id,
            "use": target.use,
            "join_keys": list(target.join_keys),
            "boundary": target.boundary,
            "endpoint_status": probe.get("endpoint_status"),
            "soda2_status": disposition["soda2_status"],
            "soda2_url": disposition["soda2_url"],
            "api_kind": probe.get("api_kind"),
            "preferred_api": disposition["preferred_api"],
            "api_priority_reason": disposition["api_priority_reason"],
            "api_url": disposition["api_url"],
            "package_resource_count": probe.get("package_resource_count"),
            "datastore_resource_count": probe.get("datastore_resource_count"),
            "latest_or_primary_total": probe.get("latest_or_primary_total"),
            "probed_total_sum": probe.get("probed_total_sum"),
            "columns": probe.get("columns") or [],
            "priority_score": score,
            "priority_band": band,
            "recommended_next_action": action,
            "probe": probe,
        }
        records.append(record)
        time.sleep(args.sleep)
    flow_summary: dict[str, Any] = {}
    for flow in [f"F{i}" for i in range(1, 8)]:
        flow_records = [r for r in records if flow in r["flows"]]
        flow_summary[flow] = {
            "sources": len(flow_records),
            "high_priority": sum(1 for r in flow_records if r["priority_band"] == "HIGH"),
            "api_probed": sum(1 for r in flow_records if r["endpoint_status"] == "API_PROBED"),
            "datastore_sources": sum(1 for r in flow_records if int(r.get("datastore_resource_count") or 0) > 0),
            "top_sources": [r["key"] for r in sorted(flow_records, key=lambda r: r["priority_score"], reverse=True)[:8]],
        }
    return {
        "task": "BARC 7-Flow Source Shape/API Scan",
        "generated_at": utc_now(),
        "status": "PASS_SOURCE_SHAPE_SCAN",
        "api_note": "Open Data BCN is CKAN-backed. No Socrata/SODA2 endpoint was found for the municipal catalogue; this scan uses CKAN DataStore/datastore_search where available as the higher-limit machine API path.",
        "soda2_disposition": {
            "status": "NO_BARCELONA_SODA2_CATALOG_FOUND",
            "decision": "Use SODA2 where a source is Socrata-backed; for Barcelona municipal/port sources, use CKAN DataStore or direct/native APIs.",
            "reason": "Open Data BCN and Port de Barcelona expose CKAN APIs, not Socrata /api/views or /resource endpoints.",
        },
        "local_landed_context": local_context,
        "flow_summary": flow_summary,
        "records": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# BARC 7-Flow Source Shape/API Scan",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Status: `{report['status']}`",
        "",
        f"API note: {report['api_note']}",
        "",
        f"SODA2 disposition: `{report.get('soda2_disposition', {}).get('status', '')}` - {report.get('soda2_disposition', {}).get('decision', '')}",
        "",
        "## Flow Summary",
        "",
        "| Flow | Sources | High priority | API probed | DataStore sources | Top sources |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for flow, row in report["flow_summary"].items():
        lines.append(
            f"| {flow} | {row['sources']} | {row['high_priority']} | {row['api_probed']} | {row['datastore_sources']} | {', '.join(row['top_sources'])} |"
        )
    lines.extend(
        [
            "",
            "## Source Matrix",
            "",
            "| Priority | Source | Flows | SODA2 | Preferred API | Count/primary total | Shape | Use | Next action |",
            "|---|---|---|---|---|---:|---|---|---|",
        ]
    )
    for row in sorted(records, key=lambda item: item["priority_score"], reverse=True):
        cols = ", ".join(str(c).replace("|", "/") for c in row.get("columns", [])[:8])
        total = row.get("latest_or_primary_total")
        total_text = f"{total:,}" if isinstance(total, int) else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{row['priority_band']} {row['priority_score']}",
                    row["key"],
                    ", ".join(row["flows"]),
                    str(row.get("soda2_status") or ""),
                    str(row.get("preferred_api") or row.get("api_kind") or ""),
                    total_text,
                    cols,
                    str(row.get("use") or "").replace("|", "/"),
                    str(row.get("recommended_next_action") or "").replace("|", "/"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This pass records shape/count/endpoint health only; it does not accept Barcelona or any flow.",
            "- No raw row samples are stored in the report; only field names/types and aggregate counts are recorded.",
            "- TMB credentials are read only from environment variables when present and are redacted from probe URLs.",
            "- Operational, public-safety, enforcement, health, traffic-control, transit-control, and port-control recommendations remain out of scope.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Barcelona 7-flow source shapes and API/count readiness.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--max-resources-per-target", type=int, default=8)
    parser.add_argument("--skip-bcn-live", action="store_true", help="Use local fallback metadata for BCN CKAN targets.")
    args = parser.parse_args()
    out = Path(args.output_dir)
    report = scan(args)
    json_write(out / "BARC_7FLOW_SOURCE_SHAPE_SCAN.json", report)
    csv_rows = []
    for row in report["records"]:
        csv_rows.append(
            {
                **row,
                "flows": ",".join(row["flows"]),
                "columns": ", ".join(row.get("columns", [])[:30]),
            }
        )
    csv_write(out / "BARC_7FLOW_SOURCE_SHAPE_SCAN.csv", csv_rows)
    (out / "BARC_7FLOW_SOURCE_SHAPE_SCAN.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Output: {out.resolve()}")
    print(f"Sources scanned: {len(report['records'])}")
    print(f"High priority: {sum(1 for row in report['records'] if row['priority_band'] == 'HIGH')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

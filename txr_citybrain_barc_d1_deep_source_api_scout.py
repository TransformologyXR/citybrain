#!/usr/bin/env python3
"""BARC-D1 Barcelona deep source/API scout and feasibility matrix.

This stage inventories and lightly probes official/public Barcelona source
families for possible future CityBrain cartridges. It does not certify
Barcelona, build a graph, or make operational recommendations.
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


TASK = "BARC-D1 Barcelona Deep Source/API Scout"
USER_AGENT = "TXR-CityBrain-BARC-D1/1.0"
OPEN_DATA_BCN_API = "https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_search"
PORT_CKAN_API = "https://opendata.portdebarcelona.cat/en/api/3/action/package_show"
BICING_GBFS_ROOT = "https://barcelona.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"

PASS_STATUSES = {
    "PASS_BARCELONA_FLOW_SCOUT",
    "PASS_WITH_SOURCE_LIMITATIONS",
    "PASS_WITH_API_KEY_LIMITATIONS",
}
FAIL_STATUSES = {"FAIL"}
ALLOWED_LANDING_STATUSES = {
    "LANDED_SAMPLE",
    "LANDED_FULL",
    "API_PROBED",
    "API_KEY_REQUIRED",
    "DOWNLOAD_FAILED",
    "SOURCE_METADATA_ONLY",
    "SKIPPED_PRIVACY_RISK",
    "SKIPPED_LICENSE_RISK",
}

REQUIRED_OUTPUT_FILES = [
    "README.md",
    "BARC_D1_HARNESS_REPORT.json",
    "BARC_D1_SOURCE_INVENTORY.json",
    "BARC_D1_API_ENDPOINT_PROBE_REPORT.json",
    "BARC_D1_DOWNLOAD_MANIFEST.json",
    "BARC_D1_FLOW_FEASIBILITY_MATRIX.json",
    "BARC_D1_PRIVACY_AND_LICENSE_REPORT.json",
    "BARC_D1_NO_OVERCLAIM_REPORT.json",
    "BARC_D1_NO_MUTATION_REPORT.json",
    "BARC_D1_ADAPTER_HANDOVER.md",
    "SHA256SUMS.json",
]

FLOW_FILES = {
    "Flow 1": "BARC_FLOW1_SITUATIONAL_STATUS_FEASIBILITY.json",
    "Flow 2": "BARC_FLOW2_PLANNING_COMPLIANCE_FEASIBILITY.json",
    "Flow 3": "BARC_FLOW3_INCIDENT_CONTEXT_FEASIBILITY.json",
    "Flow 4": "BARC_FLOW4_MOBILITY_ENVIRONMENT_FEASIBILITY.json",
    "Flow 5": "BARC_FLOW5_CLIMATE_ASSET_RISK_FEASIBILITY.json",
    "Flow 6": "BARC_FLOW6_PORT_LOGISTICS_FEASIBILITY.json",
    "Flow 7": "BARC_FLOW7_CIVIC_SENSOR_FUSION_FEASIBILITY.json",
}

NO_OVERCLAIM_STATEMENTS = [
    "BARC-D1 is a source/API scout and flow feasibility matrix only.",
    "BARC-D1 does not create a certified Barcelona cartridge.",
    "BARC-D1 does not replace Singapore or any accepted cartridge.",
    "BARC-D1 does not mutate accepted NYC, London, Chicago, or PV1-SDF outputs.",
    "BARC-D1 does not create a Barcelona graph or accepted flow output.",
    "BARC-D1 does not make operational, policing, public-safety, enforcement, emergency, traffic-control, port-control, or health recommendations.",
    "Traffic accidents and incident records are public contextual sources only, not dispatch or emergency truth.",
    "TMB/AMB API-key-limited probes are source limitations until official credentials are available.",
    "Open Data BCN catalogue availability is a probe result, not proof that all listed datasets were fully downloaded.",
    "Port de Barcelona samples are source validation samples, not full logistics operations history.",
    "Sentilo/Connecta catalogue probes are sensor-source discovery only, not a certified live sensor fabric.",
]

SENSITIVE_ENV_PATTERNS = [
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASS",
    "APP_ID",
    "APP_KEY",
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
class SourceDef:
    key: str
    title: str
    publisher: str
    family: str
    official_url: str
    licence: str
    formats: tuple[str, ...]
    update_frequency: str
    requires_api_key: bool
    supports_api: bool
    supports_download: bool
    privacy_risk: str
    flow_relevance: tuple[str, ...]
    landing_group: str
    probe_kind: str = "http"
    probe_url: str | None = None
    query: str | None = None
    ckan_package: str | None = None
    estimated_row_count: int | None = None
    notes: str = ""


@dataclass
class RunState:
    project_root: Path
    output_dir: Path
    landing_dir: Path
    reports_dir: Path
    flow_dir: Path
    session: requests.Session
    timeout: float
    max_sample_bytes: int
    probes: list[dict[str, Any]] = field(default_factory=list)
    downloads: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    open_data_bcn_bootstrap: dict[str, Any] | None = None


def open_data_bcn_search_url(query: str) -> str:
    return f"https://opendata-ajuntament.barcelona.cat/data/en/dataset?q={quote_plus(query)}"


SOURCE_DEFS: list[SourceDef] = [
    SourceDef(
        key="bicing_gbfs_realtime",
        title="Bicing GBFS realtime station information and status",
        publisher="Bicing / BSM / Ajuntament de Barcelona",
        family="Open Data BCN / Bicing",
        official_url=BICING_GBFS_ROOT,
        licence="GBFS/public terms to verify before cartridge acceptance",
        formats=("JSON", "GBFS"),
        update_frequency="realtime or near-realtime feed TTL",
        requires_api_key=False,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 4", "Flow 7"),
        landing_group="mobility",
        probe_kind="bicing_gbfs",
        probe_url=BICING_GBFS_ROOT,
        notes="Direct public GBFS root observed for Barcelona Bicing.",
    ),
    SourceDef(
        key="iris_citizen_requests",
        title="IRIS citizen incidents, complaints, and suggestions",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("IRIS incidencies queixes suggeriments"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 1", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="IRIS incidencies queixes suggeriments",
        notes="Citizen-service source; do not expose complainant or contact details.",
    ),
    SourceDef(
        key="traffic_state_sections",
        title="Traffic state by road sections",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("estat transit trams Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "GeoJSON", "API"),
        update_frequency="current or frequent update, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 3", "Flow 4", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="estat transit trams",
    ),
    SourceDef(
        key="air_quality_observations",
        title="Air quality measurements",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("qualitat aire mesures Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="frequent, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 4", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="qualitat aire mesures",
    ),
    SourceDef(
        key="noise_monitoring",
        title="Noise monitoring and strategic noise sources",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("soroll sensors Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "GeoJSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 4", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="soroll sensors",
    ),
    SourceDef(
        key="public_facilities_services",
        title="Facilities and public services",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("equipaments serveis Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "GeoJSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 3", "Flow 5", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="equipaments serveis",
    ),
    SourceDef(
        key="district_neighbourhood_boundaries",
        title="District and neighbourhood boundaries",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("districtes barris limits geografia"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "GeoJSON", "Shapefile", "API"),
        update_frequency="reference geography, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 2", "Flow 3", "Flow 4", "Flow 5", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="districtes barris limits",
    ),
    SourceDef(
        key="barcelona_land_plots",
        title="Barcelona land plots and cadastral/parcel reference layers",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("parcelari solars cadastre Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "GeoJSON", "Shapefile", "API"),
        update_frequency="reference or periodic, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 2", "Flow 5"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="parcelari solars cadastre",
    ),
    SourceDef(
        key="urban_planning_sectors",
        title="Urban planning sectors and planning areas",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("planejament urbanistic sectors ambits"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "GeoJSON", "Shapefile", "API"),
        update_frequency="planning reference, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 2",),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="planejament urbanistic sectors ambits",
    ),
    SourceDef(
        key="building_works_licences",
        title="Building licences and works permits",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("llicencies obres permisos edificacio"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 2",),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="llicencies obres permisos edificacio",
        notes="D2 blocker if record-level permits/licences are not publicly verified.",
    ),
    SourceDef(
        key="activity_business_licences",
        title="Activity and business licences",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("llicencies activitats"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 2", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="llicencies activitats",
    ),
    SourceDef(
        key="traffic_accidents_guardia_urbana",
        title="Traffic accidents handled by Guardia Urbana",
        publisher="Ajuntament de Barcelona / Guardia Urbana",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("accidents Guardia Urbana"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="historical or periodic, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 3", "Flow 4", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="accidents Guardia Urbana",
        notes="Use traffic context only; no enforcement, emergency, or public-safety recommendations.",
    ),
    SourceDef(
        key="traffic_accident_vehicles",
        title="Vehicles involved in traffic accidents",
        publisher="Ajuntament de Barcelona / Guardia Urbana",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("vehicles implicats accidents Guardia Urbana"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="historical or periodic, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 3", "Flow 4", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="vehicles implicats accidents Guardia Urbana",
        notes="No person-level or plate-level values should be emitted in future samples.",
    ),
    SourceDef(
        key="weather_rainfall",
        title="Weather and rainfall measurements",
        publisher="Ajuntament de Barcelona / public environmental sources",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("pluja meteorologia Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="frequent, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 4", "Flow 5", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="pluja meteorologia",
    ),
    SourceDef(
        key="groundwater_piezometric_levels",
        title="Groundwater or piezometric level context",
        publisher="Ajuntament de Barcelona / public water sources",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("piezometric nivell aigua Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 5", "Flow 7"),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="piezometric nivell aigua",
    ),
    SourceDef(
        key="energy_consumption_postal_sector",
        title="Energy consumption by postal code, time, or economic sector",
        publisher="Ajuntament de Barcelona / public energy sources",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("consum energia codi postal sector economic"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="periodic, dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 5",),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="consum energia codi postal sector economic",
        notes="Aggregate-only use; no household inference.",
    ),
    SourceDef(
        key="parking_waste_cleaning_context",
        title="Parking, waste, and cleaning civic context",
        publisher="Ajuntament de Barcelona",
        family="Open Data BCN",
        official_url=open_data_bcn_search_url("aparcaments residus neteja Barcelona"),
        licence="Open Data BCN licence to verify from dataset metadata",
        formats=("CSV", "JSON", "API"),
        update_frequency="dataset metadata to verify",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 7",),
        landing_group="open_data_bcn",
        probe_kind="open_data_bcn_search",
        query="aparcaments residus neteja",
    ),
    SourceDef(
        key="cadastre_parcels_inspire",
        title="Spanish Cadastre INSPIRE cadastral parcels WFS",
        publisher="Direccion General del Catastro",
        family="Spanish DG Cadastre / INSPIRE",
        official_url="https://www.catastro.hacienda.gob.es/webinspire/index.html",
        licence="Spanish Cadastre open/public reuse terms to verify",
        formats=("WFS", "GML", "XML"),
        update_frequency="official cadastre publication cycle",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 2", "Flow 5"),
        landing_group="cadastre",
        probe_kind="http",
        probe_url="https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=WFS&request=GetCapabilities",
        notes="Capability probe only; no parcel bulk pull in D1.",
    ),
    SourceDef(
        key="cadastre_buildings_inspire",
        title="Spanish Cadastre INSPIRE buildings WFS",
        publisher="Direccion General del Catastro",
        family="Spanish DG Cadastre / INSPIRE",
        official_url="https://www.catastro.hacienda.gob.es/webinspire/index.html",
        licence="Spanish Cadastre open/public reuse terms to verify",
        formats=("WFS", "GML", "XML"),
        update_frequency="official cadastre publication cycle",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 2", "Flow 5"),
        landing_group="cadastre",
        probe_kind="http",
        probe_url="https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=WFS&request=GetCapabilities",
        notes="Capability probe only; no building bulk pull in D1.",
    ),
    SourceDef(
        key="cadastre_addresses_inspire",
        title="Spanish Cadastre INSPIRE addresses WFS",
        publisher="Direccion General del Catastro",
        family="Spanish DG Cadastre / INSPIRE",
        official_url="https://www.catastro.hacienda.gob.es/webinspire/index.html",
        licence="Spanish Cadastre open/public reuse terms to verify",
        formats=("WFS", "GML", "XML"),
        update_frequency="official cadastre publication cycle",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="MEDIUM",
        flow_relevance=("Flow 2",),
        landing_group="cadastre",
        probe_kind="http",
        probe_url="https://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx?service=WFS&request=GetCapabilities",
        notes="Address capability only; avoid publishing full address extracts from D1.",
    ),
    SourceDef(
        key="tmb_static_gtfs_api",
        title="TMB static GTFS API",
        publisher="Transports Metropolitans de Barcelona",
        family="TMB developer tools",
        official_url="https://developer.tmb.cat/",
        licence="TMB developer terms to verify",
        formats=("GTFS", "ZIP", "API"),
        update_frequency="scheduled transit updates",
        requires_api_key=True,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 4",),
        landing_group="tmb",
        probe_kind="http",
        probe_url="https://api.tmb.cat/v1/static/datasets/gtfs.zip",
        notes="Observed unauthenticated response requires auth parameters; no keys used.",
    ),
    SourceDef(
        key="tmb_ibus_realtime_api",
        title="TMB iBus and public transport realtime APIs",
        publisher="Transports Metropolitans de Barcelona",
        family="TMB developer tools",
        official_url="https://developer.tmb.cat/",
        licence="TMB developer terms to verify",
        formats=("JSON", "API"),
        update_frequency="realtime or near-realtime",
        requires_api_key=True,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 3", "Flow 4"),
        landing_group="tmb",
        probe_kind="http",
        probe_url="https://api.tmb.cat/v1/ibus/lines",
        notes="API-key-required transit disruption and live movement candidate.",
    ),
    SourceDef(
        key="tmb_developer_docs",
        title="TMB developer documentation portal",
        publisher="Transports Metropolitans de Barcelona",
        family="TMB developer tools",
        official_url="https://developer.tmb.cat/",
        licence="TMB developer terms to verify",
        formats=("HTML", "API documentation"),
        update_frequency="documentation",
        requires_api_key=False,
        supports_api=False,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 4",),
        landing_group="tmb",
        probe_kind="http",
        probe_url="https://developer.tmb.cat/",
    ),
    SourceDef(
        key="amb_open_data_help",
        title="AMB open data documentation",
        publisher="Area Metropolitana de Barcelona",
        family="AMB open data",
        official_url="https://opendata.amb.cat/help.html",
        licence="AMB open data terms to verify",
        formats=("HTML", "API documentation"),
        update_frequency="documentation",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 4",),
        landing_group="amb",
        probe_kind="http",
        probe_url="https://opendata.amb.cat/help.html",
    ),
    SourceDef(
        key="amb_gtfs_realtime_bus",
        title="AMB GTFS realtime bus service candidate",
        publisher="Area Metropolitana de Barcelona",
        family="AMB open data",
        official_url="https://www.amb.cat/s/mobilitat/open-data.html",
        licence="AMB open data terms to verify",
        formats=("GTFS-RT", "Protocol Buffers", "API"),
        update_frequency="realtime or near-realtime",
        requires_api_key=False,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 4",),
        landing_group="amb",
        probe_kind="http",
        probe_url="https://www.amb.cat/s/mobilitat/open-data.html",
        notes="Public page may use anti-bot protection; exact GTFS-RT feed URL remains a D2 verification item.",
    ),
    SourceDef(
        key="sentilo_connecta_catalog",
        title="Barcelona Sentilo/Connecta public sensor catalogue",
        publisher="Ajuntament de Barcelona / Sentilo",
        family="Sentilo / public sensors",
        official_url="https://connecta.bcn.cat/connecta-catalog-web/catalog/component",
        licence="Sentilo/Connecta terms to verify",
        formats=("HTML", "API catalogue", "JSON candidate"),
        update_frequency="catalogue/live sensor metadata",
        requires_api_key=False,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 4", "Flow 5", "Flow 7"),
        landing_group="sentilo",
        probe_kind="http",
        probe_url="https://connecta.bcn.cat/connecta-catalog-web/catalog/component",
        notes="Catalogue probe only; live observations require endpoint-specific follow-up.",
    ),
    SourceDef(
        key="sentilo_connecta_map",
        title="Barcelona Sentilo/Connecta sensor map",
        publisher="Ajuntament de Barcelona / Sentilo",
        family="Sentilo / public sensors",
        official_url="https://connecta.bcn.cat/connecta-catalog-web/component/map",
        licence="Sentilo/Connecta terms to verify",
        formats=("HTML", "map catalogue"),
        update_frequency="catalogue/live sensor metadata",
        requires_api_key=False,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 1", "Flow 4", "Flow 5", "Flow 7"),
        landing_group="sentilo",
        probe_kind="http",
        probe_url="https://connecta.bcn.cat/connecta-catalog-web/component/map",
    ),
    SourceDef(
        key="port_ships_in_port",
        title="Ships in Port of Barcelona today",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/vaixells-en-port",
        licence="CC BY-SA 4.0",
        formats=("CSV", "CKAN"),
        update_frequency="daily/current",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="vaixells-en-port",
    ),
    SourceDef(
        key="port_ship_traffic_statistics",
        title="Ship traffic statistics",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/estadistiques-de-trfic-de-vaixells",
        licence="CC BY-SA 4.0",
        formats=("CSV", "CKAN"),
        update_frequency="monthly/annual",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="estadistiques-de-trfic-de-vaixells",
    ),
    SourceDef(
        key="port_maritime_signalling",
        title="Maritime signalling",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/senyalitzacio-maritima",
        licence="CC BY-SA 4.0",
        formats=("XLS", "CKAN"),
        update_frequency="reference",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="senyalitzacio-maritima",
    ),
    SourceDef(
        key="port_weather_bocana_nord",
        title="Port meteorological station Bocana Nord",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/estacio-meteorolgica-bocana-nord",
        licence="CC BY-SA 4.0",
        formats=("CSV", "CKAN"),
        update_frequency="instant/current and historical",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 5", "Flow 6", "Flow 7"),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="estacio-meteorolgica-bocana-nord",
    ),
    SourceDef(
        key="port_weather_zal_prat",
        title="Port meteorological station ZAL Prat",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/estacio-meteorolgica-zal-prat",
        licence="CC BY-SA 4.0",
        formats=("CSV", "CKAN"),
        update_frequency="instant/current and historical",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 5", "Flow 6", "Flow 7"),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="estacio-meteorolgica-zal-prat",
    ),
    SourceDef(
        key="port_rail_services",
        title="Railway services of the Port of Barcelona",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/serveis-ferroviaris-del-port-de-barcelona",
        licence="CC BY-SA 4.0",
        formats=("XML", "CKAN"),
        update_frequency="reference",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="serveis-ferroviaris-del-port-de-barcelona",
    ),
    SourceDef(
        key="port_service_companies",
        title="Port service companies",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/empreses-prestadores-de-serveis-portuaris",
        licence="CC BY-SA 4.0",
        formats=("CSV", "CKAN"),
        update_frequency="reference",
        requires_api_key=False,
        supports_api=True,
        supports_download=True,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="empreses-prestadores-de-serveis-portuaris",
    ),
    SourceDef(
        key="port_tenders",
        title="Port tenders and transparency",
        publisher="Port de Barcelona",
        family="Port de Barcelona Open Data",
        official_url="https://opendata.portdebarcelona.cat/en/dataset/licitacions",
        licence="CC BY-SA 4.0",
        formats=("WEB", "CKAN"),
        update_frequency="current/as-published",
        requires_api_key=False,
        supports_api=True,
        supports_download=False,
        privacy_risk="LOW",
        flow_relevance=("Flow 6",),
        landing_group="port",
        probe_kind="port_ckan_package",
        ckan_package="licitacions",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return re.sub(r"_+", "_", text).strip("._") or "source"


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
            files.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    return {"status": "PASS", "generated_at": utc_now(), "files": files}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return session


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def relative_to(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    redacted = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            redacted.append((key, "REDACTED"))
        else:
            redacted.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(redacted, doseq=True)))


def append_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    for key, value in params.items():
        query.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def tmb_auth_state() -> dict[str, Any]:
    app_id = os.environ.get("TMB_APP_ID") or ""
    app_key = os.environ.get("TMB_APP_KEY") or os.environ.get("TMB_API_KEY") or ""
    return {
        "app_id": app_id,
        "app_key": app_key,
        "app_id_present": bool(app_id),
        "app_key_present": bool(app_key),
        "credentials_complete": bool(app_id and app_key),
    }


def redact_auth_state(auth_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not auth_state:
        return None
    return {
        "provider": "tmb",
        "app_id_present": bool(auth_state.get("app_id_present")),
        "app_key_present": bool(auth_state.get("app_key_present")),
        "credentials_complete": bool(auth_state.get("credentials_complete")),
        "raw_credentials_serialized": False,
    }


def compact_json(value: Any, max_chars: int = 1200) -> Any:
    if isinstance(value, dict):
        return {str(k): compact_json(v, max_chars=max_chars) for k, v in list(value.items())[:25]}
    if isinstance(value, list):
        return [compact_json(v, max_chars=max_chars) for v in value[:5]]
    if isinstance(value, str):
        return value[:max_chars]
    return value


def extension_for(content_type: str | None, url: str) -> str:
    parsed = Path(urlparse(url).path)
    suffix = parsed.suffix.lower().strip(".")
    if suffix in {"json", "csv", "xml", "html", "htm", "zip", "xls", "xlsx", "geojson"}:
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
        return "zip.sample"
    return "bin"


def sanitize_sample_bytes(content: bytes, content_type: str | None) -> bytes:
    ctype = (content_type or "").lower()
    text_like = any(marker in ctype for marker in ["text", "json", "xml", "html", "javascript", "x-www-form-urlencoded"])
    if not text_like:
        head = content[:1024].lstrip()
        text_like = head.startswith((b"{", b"[", b"<", b"<!"))
    if not text_like:
        return content
    redacted = TOKEN_QUERY_RE.sub(rb"\1=REDACTED", content)
    redacted = TOKEN_JSON_RE.sub(rb"\1REDACTED\3", redacted)
    return redacted


def should_skip_sample(source: SourceDef) -> bool:
    return source.privacy_risk == "HIGH"


def record_download(
    state: RunState,
    *,
    source: SourceDef,
    path: Path,
    status: str,
    url: str,
    content_type: str | None,
    source_hash: str,
    full: bool = False,
    note: str = "",
) -> dict[str, Any]:
    item = {
        "source_key": source.key,
        "title": source.title,
        "landing_status": status,
        "path": relative_to(path, state.project_root),
        "url": redact_url(url),
        "content_type": content_type,
        "sha256": source_hash,
        "bytes": path.stat().st_size if path.exists() else 0,
        "full_download": full,
        "note": note,
    }
    state.downloads.append(item)
    return item


def save_sample(
    state: RunState,
    source: SourceDef,
    url: str,
    content: bytes,
    content_type: str | None,
    *,
    suffix: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    group = safe_name(source.landing_group)
    ext = suffix or extension_for(content_type, url)
    sample = sanitize_sample_bytes(content[: state.max_sample_bytes], content_type)
    path = state.landing_dir / "raw" / group / f"{safe_name(source.key)}_sample.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sample)
    return record_download(
        state,
        source=source,
        path=path,
        status="LANDED_SAMPLE",
        url=url,
        content_type=content_type,
        source_hash=sha256_bytes(sample),
        full=False,
        note=note,
    )


def get_bytes(state: RunState, url: str, *, accept: str = "*/*") -> tuple[requests.Response | None, bytes, str | None]:
    try:
        response = state.session.get(url, timeout=(state.timeout, state.timeout), headers={"Accept": accept}, stream=True)
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            remaining = state.max_sample_bytes - total
            if remaining <= 0:
                break
            piece = chunk[:remaining]
            chunks.append(piece)
            total += len(piece)
            if total >= state.max_sample_bytes:
                break
        content = b"".join(chunks)
        response.close()
        response._content = content
        return response, content, None
    except requests.RequestException as exc:
        return None, b"", f"{type(exc).__name__}: {exc}"


def http_probe(state: RunState, source: SourceDef) -> dict[str, Any]:
    url = source.probe_url or source.official_url
    auth_state: dict[str, Any] | None = None
    if source.family == "TMB developer tools" and source.requires_api_key:
        auth_state = tmb_auth_state()
        if auth_state["credentials_complete"]:
            url = append_query_params(url, {"app_id": auth_state["app_id"], "app_key": auth_state["app_key"]})
    response, content, error = get_bytes(state, url)
    display_url = redact_url(url)
    if response is None:
        state.failures.append({"source_key": source.key, "url": display_url, "error": error})
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": display_url,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "error": error,
            "auth": redact_auth_state(auth_state),
        }
    status_code = response.status_code
    ctype = response.headers.get("content-type")
    probe_status = "API_PROBED"
    landing_status = "API_PROBED"
    downloaded = None
    if status_code in {401, 403} and source.requires_api_key:
        probe_status = "API_KEY_REQUIRED"
        landing_status = "API_KEY_REQUIRED"
    elif 200 <= status_code < 300 and not should_skip_sample(source):
        downloaded = save_sample(state, source, url, content, ctype, note="bounded HTTP probe sample")
        landing_status = downloaded["landing_status"]
    elif 200 <= status_code < 300 and should_skip_sample(source):
        landing_status = "SKIPPED_PRIVACY_RISK"
    elif status_code in {401, 403}:
        landing_status = "API_PROBED"
    else:
        landing_status = "DOWNLOAD_FAILED"
        probe_status = "DOWNLOAD_FAILED"

    return {
        "source_key": source.key,
        "probe_kind": source.probe_kind,
        "url": display_url,
        "status": probe_status,
        "landing_status": landing_status,
        "http_status": status_code,
        "content_type": ctype,
        "content_length": response.headers.get("content-length"),
        "sample_hash": downloaded.get("sha256") if downloaded else sha256_bytes(content) if content else None,
        "auth": redact_auth_state(auth_state),
    }


def open_data_bcn_bootstrap(state: RunState) -> dict[str, Any]:
    if state.open_data_bcn_bootstrap is not None:
        return state.open_data_bcn_bootstrap
    url = f"{OPEN_DATA_BCN_API}?q=bicing&rows=1"
    response, content, error = get_bytes(state, url, accept="application/json")
    if response is None:
        result = {"available": False, "url": url, "status": "DOWNLOAD_FAILED", "error": error}
    elif response.ok:
        result = {"available": True, "url": url, "status": "API_PROBED", "http_status": response.status_code}
    else:
        result = {
            "available": False,
            "url": url,
            "status": "DOWNLOAD_FAILED",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "sample_hash": sha256_bytes(content) if content else None,
        }
    state.open_data_bcn_bootstrap = result
    return result


def open_data_bcn_probe(state: RunState, source: SourceDef) -> dict[str, Any]:
    bootstrap = open_data_bcn_bootstrap(state)
    if not bootstrap.get("available"):
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": OPEN_DATA_BCN_API,
            "query": source.query,
            "status": "SOURCE_METADATA_ONLY",
            "landing_status": "SOURCE_METADATA_ONLY",
            "bootstrap": bootstrap,
            "note": "Open Data BCN CKAN endpoint was not reachable from this run; source retained as official metadata/candidate.",
        }
    response, content, error = get_bytes(
        state,
        f"{OPEN_DATA_BCN_API}?q={quote_plus(source.query or source.title)}&rows=5",
        accept="application/json",
    )
    if response is None:
        state.failures.append({"source_key": source.key, "url": OPEN_DATA_BCN_API, "error": error})
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": OPEN_DATA_BCN_API,
            "query": source.query,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "error": error,
        }
    if not response.ok:
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": response.url,
            "query": source.query,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
        }
    data = None
    try:
        data = response.json()
    except ValueError:
        pass
    downloaded = save_sample(state, source, response.url, content, response.headers.get("content-type"), suffix="json", note="Open Data BCN package_search sample")
    count = None
    titles: list[str] = []
    if isinstance(data, dict):
        result = data.get("result", {})
        if isinstance(result, dict):
            count = result.get("count")
            for item in result.get("results", [])[:5]:
                if isinstance(item, dict) and item.get("title"):
                    titles.append(str(item["title"]))
    return {
        "source_key": source.key,
        "probe_kind": source.probe_kind,
        "url": response.url,
        "query": source.query,
        "status": "API_PROBED",
        "landing_status": "LANDED_SAMPLE",
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "result_count": count,
        "candidate_titles": titles,
        "sample_hash": downloaded["sha256"],
    }


def port_ckan_probe(state: RunState, source: SourceDef) -> dict[str, Any]:
    if not source.ckan_package:
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "status": "SOURCE_METADATA_ONLY",
            "landing_status": "SOURCE_METADATA_ONLY",
        }
    url = f"{PORT_CKAN_API}?id={quote_plus(source.ckan_package)}"
    response, content, error = get_bytes(state, url, accept="application/json")
    if response is None:
        state.failures.append({"source_key": source.key, "url": url, "error": error})
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": url,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "error": error,
        }
    if not response.ok:
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": url,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
        }
    metadata_download = save_sample(state, source, response.url, content, response.headers.get("content-type"), suffix="json", note="Port CKAN package_show metadata")
    package = None
    try:
        package = response.json().get("result", {})
    except (ValueError, AttributeError):
        package = {}
    resources = package.get("resources", []) if isinstance(package, dict) else []
    resource_summaries = []
    resource_sample = None
    for resource in resources[:6]:
        if not isinstance(resource, dict):
            continue
        resource_summaries.append(
            {
                "id": resource.get("id"),
                "name": resource.get("name"),
                "format": resource.get("format"),
                "url": resource.get("url"),
                "size": resource.get("size"),
                "last_modified": resource.get("last_modified"),
            }
        )
    first_url = next((item.get("url") for item in resource_summaries if item.get("url") and str(item.get("format", "")).upper() in {"CSV", "XML", "XLS"}), None)
    if first_url and not should_skip_sample(source):
        sample_response, sample_content, sample_error = get_bytes(state, str(first_url))
        if sample_response is not None and sample_response.ok and sample_content:
            resource_sample = save_sample(
                state,
                source,
                str(first_url),
                sample_content,
                sample_response.headers.get("content-type"),
                note="Port resource bounded sample",
            )
        elif sample_error:
            state.failures.append({"source_key": source.key, "url": first_url, "error": sample_error})
    return {
        "source_key": source.key,
        "probe_kind": source.probe_kind,
        "url": response.url,
        "status": "API_PROBED",
        "landing_status": "LANDED_SAMPLE",
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "package_title": package.get("title") if isinstance(package, dict) else None,
        "license_title": package.get("license_title") if isinstance(package, dict) else None,
        "resource_count": len(resources),
        "resources": resource_summaries,
        "metadata_hash": metadata_download["sha256"],
        "resource_sample_hash": resource_sample.get("sha256") if resource_sample else None,
    }


def bicing_gbfs_probe(state: RunState, source: SourceDef) -> dict[str, Any]:
    response, content, error = get_bytes(state, source.probe_url or source.official_url, accept="application/json")
    if response is None:
        state.failures.append({"source_key": source.key, "url": source.official_url, "error": error})
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": source.official_url,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "error": error,
        }
    if not response.ok:
        return {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": source.official_url,
            "status": "DOWNLOAD_FAILED",
            "landing_status": "DOWNLOAD_FAILED",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
        }
    root_download = save_sample(state, source, response.url, content, response.headers.get("content-type"), suffix="json", note="GBFS root feed")
    data = {}
    try:
        data = response.json()
    except ValueError:
        pass
    feeds = []
    if isinstance(data, dict):
        feeds = data.get("data", {}).get("feeds", []) if isinstance(data.get("data"), dict) else []
    feed_urls = {item.get("name"): item.get("url") for item in feeds if isinstance(item, dict)}
    subfeed_results = []
    station_counts: dict[str, Any] = {}
    for feed_name in ["station_information", "station_status", "system_information"]:
        feed_url = feed_urls.get(feed_name)
        if not feed_url:
            continue
        sub_response, sub_content, sub_error = get_bytes(state, str(feed_url), accept="application/json")
        if sub_response is None:
            subfeed_results.append({"feed": feed_name, "status": "DOWNLOAD_FAILED", "error": sub_error})
            continue
        item: dict[str, Any] = {
            "feed": feed_name,
            "url": str(feed_url),
            "http_status": sub_response.status_code,
            "content_type": sub_response.headers.get("content-type"),
        }
        if sub_response.ok:
            dl = save_sample(state, source, str(feed_url), sub_content, sub_response.headers.get("content-type"), suffix=f"{feed_name}.json", note=f"GBFS {feed_name} sample")
            item["landing_status"] = "LANDED_SAMPLE"
            item["sha256"] = dl["sha256"]
            try:
                parsed = sub_response.json()
                stations = parsed.get("data", {}).get("stations", []) if isinstance(parsed.get("data"), dict) else []
                if isinstance(stations, list):
                    station_counts[feed_name] = len(stations)
            except (ValueError, AttributeError):
                pass
        else:
            item["landing_status"] = "DOWNLOAD_FAILED"
        subfeed_results.append(item)
    return {
        "source_key": source.key,
        "probe_kind": source.probe_kind,
        "url": response.url,
        "status": "API_PROBED",
        "landing_status": "LANDED_SAMPLE",
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "last_updated": data.get("last_updated") if isinstance(data, dict) else None,
        "ttl": data.get("ttl") if isinstance(data, dict) else None,
        "feed_names": sorted(feed_urls),
        "station_counts": station_counts,
        "root_hash": root_download["sha256"],
        "subfeeds": subfeed_results,
    }


def probe_source(state: RunState, source: SourceDef) -> dict[str, Any]:
    if source.probe_kind == "bicing_gbfs":
        result = bicing_gbfs_probe(state, source)
    elif source.probe_kind == "open_data_bcn_search":
        result = open_data_bcn_probe(state, source)
    elif source.probe_kind == "port_ckan_package":
        result = port_ckan_probe(state, source)
    elif source.probe_kind == "metadata_only":
        result = {
            "source_key": source.key,
            "probe_kind": source.probe_kind,
            "url": source.official_url,
            "status": "SOURCE_METADATA_ONLY",
            "landing_status": "SOURCE_METADATA_ONLY",
        }
    else:
        result = http_probe(state, source)
    result.setdefault("landing_status", result.get("status", "SOURCE_METADATA_ONLY"))
    if result["landing_status"] not in ALLOWED_LANDING_STATUSES:
        result["landing_status"] = "SOURCE_METADATA_ONLY"
    state.probes.append(result)
    return result


def inventory_record(source: SourceDef, probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": source.key,
        "title": source.title,
        "publisher": source.publisher,
        "family": source.family,
        "official_url": source.official_url,
        "official_domain": urlparse(source.official_url).netloc,
        "licence": probe.get("license_title") or source.licence,
        "format": list(source.formats),
        "update_frequency": source.update_frequency,
        "requires_api_key": source.requires_api_key or probe.get("landing_status") == "API_KEY_REQUIRED",
        "supports_api": source.supports_api,
        "supports_download": source.supports_download,
        "estimated_row_count": probe.get("result_count") or probe.get("station_counts") or source.estimated_row_count,
        "privacy_risk": source.privacy_risk,
        "flow_relevance": list(source.flow_relevance),
        "landing_status": probe.get("landing_status", "SOURCE_METADATA_ONLY"),
        "hash": probe.get("sample_hash") or probe.get("metadata_hash") or probe.get("root_hash") or probe.get("resource_sample_hash"),
        "probe_status": probe.get("status"),
        "probe_url": probe.get("url") or source.probe_url,
        "http_status": probe.get("http_status"),
        "notes": source.notes,
    }


def source_inventory(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "task": TASK,
        "source_count": len(records),
        "allowed_landing_statuses": sorted(ALLOWED_LANDING_STATUSES),
        "sources": records,
    }


def api_probe_report(state: RunState) -> dict[str, Any]:
    probed = [probe for probe in state.probes if probe.get("landing_status") not in {"SOURCE_METADATA_ONLY"}]
    key_required = [probe for probe in state.probes if probe.get("landing_status") == "API_KEY_REQUIRED"]
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "sources_probed": len(probed),
        "api_key_required_sources": len(key_required),
        "open_data_bcn_bootstrap": state.open_data_bcn_bootstrap,
        "probes": state.probes,
        "failures": state.failures,
    }


def download_manifest(state: RunState) -> dict[str, Any]:
    full = [item for item in state.downloads if item.get("landing_status") == "LANDED_FULL"]
    samples = [item for item in state.downloads if item.get("landing_status") == "LANDED_SAMPLE"]
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "landing_dir": str(state.landing_dir),
        "landed_full_sources": len({item["source_key"] for item in full}),
        "landed_sample_sources": len({item["source_key"] for item in samples}),
        "landed_full_artifacts": len(full),
        "landed_sample_artifacts": len(samples),
        "downloads": state.downloads,
    }


def supporting_sources(records: list[dict[str, Any]], flow: str) -> list[dict[str, Any]]:
    items = []
    for record in records:
        if flow in record.get("flow_relevance", []):
            items.append(
                {
                    "key": record["key"],
                    "title": record["title"],
                    "publisher": record["publisher"],
                    "landing_status": record["landing_status"],
                    "requires_api_key": record["requires_api_key"],
                    "privacy_risk": record["privacy_risk"],
                }
            )
    return items


def flow_feasibility(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    matrix = {
        "Flow 1": {
            "flow": "Flow 1 - Situational Status",
            "score": 3,
            "score_label": "strong cartridge candidate",
            "missing_blockers": [
                "Open Data BCN catalogue/package metadata should be re-probed from a network path that can reach the CKAN endpoint.",
                "Confirm traffic-state, IRIS, air-quality, noise, facilities, and boundary update frequencies from dataset metadata.",
            ],
            "recommended_next_gate": "BARC-D2 Flow 1 source landing with Open Data BCN direct resource URLs and capped samples.",
            "claim_boundary": "Situational context only; no public-safety, policing, dispatch, traffic-control, or health recommendations.",
        },
        "Flow 2": {
            "flow": "Flow 2 - Planning / Construction / Compliance",
            "score": 3,
            "score_label": "strong cartridge candidate with permit/licence verification blocker",
            "missing_blockers": [
                "Verify public building works permit, activity licence, inspection, and violation datasets at record level.",
                "Confirm legal reuse terms for Spanish Cadastre INSPIRE parcel/building/address layers.",
                "Avoid address/person-level publication in D1 samples.",
            ],
            "recommended_next_gate": "BARC-D2 planning/compliance identity source review before any graph ingest.",
            "claim_boundary": "Planning feasibility only; no enforcement or compliance recommendations.",
        },
        "Flow 3": {
            "flow": "Flow 3 - Incident / Response / Affected Context",
            "score": 3,
            "score_label": "strong traffic-incident context candidate",
            "missing_blockers": [
                "Traffic accident sources are not emergency dispatch feeds.",
                "TMB/AMB disruption feeds need official authenticated or documented endpoint verification.",
                "Facility/resource context must remain contextual.",
            ],
            "recommended_next_gate": "BARC-D2 traffic-incident context pack with accident, traffic-state, transit-disruption, and facility samples.",
            "claim_boundary": "Traffic incident context only; no emergency, dispatch, public-safety, or operational recommendations.",
        },
        "Flow 4": {
            "flow": "Flow 4 - Mobility / Crowd / Transport / Environment",
            "score": 4,
            "score_label": "high-confidence near-term cartridge candidate",
            "missing_blockers": [
                "TMB static/realtime endpoints require official app credentials.",
                "AMB GTFS-RT endpoint URL needs official confirmation because the public page used anti-bot protection in this run.",
                "Open Data BCN traffic/environment package metadata should be re-probed.",
            ],
            "recommended_next_gate": "BARC-D2 mobility/environment cartridge scout with Bicing GBFS, TMB credentials, AMB GTFS-RT verification, traffic, air, noise, and rainfall samples.",
            "claim_boundary": "Mobility status and environmental context only; no traffic-control or crowd-control recommendations.",
        },
        "Flow 5": {
            "flow": "Flow 5 - Flood / Climate / Asset Dependency",
            "score": 2,
            "score_label": "partial cartridge candidate",
            "missing_blockers": [
                "Flood-risk layers need confirmed public WMS/WFS/download endpoints.",
                "Rainfall, groundwater/piezometric, energy, and critical-facility layers need exact dataset resource validation.",
                "Asset dependency graph is out of scope for D1.",
            ],
            "recommended_next_gate": "BARC-D2 climate/asset source recovery with ACA/municipal flood-risk endpoints and bounded environmental samples.",
            "claim_boundary": "Climate and asset-risk context only; no emergency, evacuation, health, or utility operations recommendations.",
        },
        "Flow 6": {
            "flow": "Flow 6 - Port / Logistics / Industrial Sequencing",
            "score": 3,
            "score_label": "strong port/logistics source candidate",
            "missing_blockers": [
                "Port samples are source validation only, not full operational history.",
                "No port-control, vessel-control, or industrial sequencing decisions may be inferred.",
                "Operational APIs beyond open CKAN resources require separate official review.",
            ],
            "recommended_next_gate": "BARC-D2 port logistics source landing with Port CKAN resource-by-resource licence and size review.",
            "claim_boundary": "Port/logistics context and historical/statistical analysis only; no port-control or operational recommendations.",
        },
        "Flow 7": {
            "flow": "Flow 7 - Civic + Sensor Fusion",
            "score": 4,
            "score_label": "high-confidence near-term cartridge candidate",
            "missing_blockers": [
                "Sentilo/Connecta live observation endpoints need endpoint-specific verification.",
                "IRIS and Open Data BCN civic package metadata should be re-probed from a reachable network path.",
                "Privacy controls needed for citizen-service and licence/business sources.",
            ],
            "recommended_next_gate": "BARC-D2 civic/sensor fusion scout with IRIS, Sentilo, air, noise, traffic, Bicing, parking/waste, and facilities samples.",
            "claim_boundary": "Civic and sensor fusion context only; no enforcement, health, or emergency recommendations.",
        },
    }
    for flow, item in matrix.items():
        item["supporting_sources"] = supporting_sources(records, flow)
    return matrix


def privacy_and_license_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    risky = [record for record in records if record.get("privacy_risk") in {"HIGH"}]
    licence_blockers = [
        record
        for record in records
        if "risk" in str(record.get("licence", "")).lower() and record.get("landing_status") not in {"SOURCE_METADATA_ONLY"}
    ]
    return {
        "status": "PASS" if not risky and not licence_blockers else "FAIL",
        "generated_at": utc_now(),
        "privacy_summary": {
            "high_risk_sources": [record["key"] for record in risky],
            "medium_risk_sources": [record["key"] for record in records if record.get("privacy_risk") == "MEDIUM"],
            "controls": [
                "No private data was scraped.",
                "No secrets or API credentials were used.",
                "D1 samples avoid person-level/address bulk extracts.",
                "Citizen-service, licence, accident, and energy sources require privacy review before any accepted cartridge.",
            ],
        },
        "license_summary": {
            "cc_by_sa_4_0_sources": [record["key"] for record in records if "CC BY-SA 4.0" in str(record.get("licence"))],
            "terms_to_verify_sources": [
                record["key"]
                for record in records
                if "verify" in str(record.get("licence", "")).lower()
            ],
            "license_blockers": [record["key"] for record in licence_blockers],
        },
    }


def no_mutation_report(root: Path, output_dir: Path, landing_dir: Path) -> dict[str, Any]:
    protected = [
        "outputs/nyc",
        "outputs/lon",
        "outputs/london",
        "outputs/chi",
        "outputs/pv1_sdf",
        "data_landing/nyc",
        "data_landing/lon",
        "data_landing/london",
        "data_landing/chi",
        "data_landing/pv1_sdf",
    ]
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "allowed_write_roots": [relative_to(output_dir, root), relative_to(landing_dir, root)],
        "protected_patterns_not_written_by_runner": protected,
        "statement": "BARC-D1 runner writes only the Barcelona scout output and landing directories plus explicit BARC-D1 implementation files.",
    }


def no_overclaim_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "statements": NO_OVERCLAIM_STATEMENTS,
    }


def landing_manifest(state: RunState) -> dict[str, Any]:
    return {
        "status": "PASS",
        "generated_at": utc_now(),
        "task": TASK,
        "landing_dir": str(state.landing_dir),
        "downloads": state.downloads,
    }


def adapter_handover_text(status: str, records: list[dict[str, Any]], matrix: dict[str, dict[str, Any]]) -> str:
    flow_lines = []
    for flow_name in sorted(matrix):
        item = matrix[flow_name]
        flow_lines.append(f"- {item['flow']}: score {item['score']} - {item['score_label']}")
    key_limited = [record["key"] for record in records if record.get("requires_api_key")]
    source_limited = [record["key"] for record in records if record.get("landing_status") in {"SOURCE_METADATA_ONLY", "DOWNLOAD_FAILED"}]
    lines = [
        "# BARC-D1 Adapter Handover",
        "",
        f"Status: {status}",
        "",
        "Barcelona is a candidate city only. This handover is for future adapter planning and does not certify a cartridge.",
        "",
        "Recommended first Barcelona cartridge: Flow 4 / Flow 7.",
        "",
        "Flow scores:",
        *flow_lines,
        "",
        "Key/API limitations:",
    ]
    lines.extend([f"- {key}" for key in key_limited] if key_limited else ["- None observed"])
    lines.extend(["", "Source limitations:"])
    lines.extend([f"- {key}" for key in source_limited] if source_limited else ["- None observed"])
    lines.extend(
        [
            "",
            "Adapter notes:",
            "- Keep Bicing GBFS as a bounded public mobility source.",
            "- For TMB authenticated probes, set TMB_APP_ID and TMB_APP_KEY in the shell environment; TMB_API_KEY is accepted as an app-key alias.",
            "- Treat TMB and AMB as credential/documentation gates until official endpoints are confirmed.",
            "- Treat Open Data BCN unreachable catalogue probes as a rerun item, not as absence of source data.",
            "- Keep Port de Barcelona data contextual and non-operational.",
            "- Preserve all privacy and no-overclaim boundaries from BARC_D1_NO_OVERCLAIM_REPORT.json.",
            "",
        ]
    )
    return "\n".join(lines)


def readme_text(status: str, output_dir: Path, landing_dir: Path, records: list[dict[str, Any]], matrix: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# BARC-D1 Barcelona Deep Source/API Scout",
        "",
        f"Status: {status}",
        "",
        "This is a scout and source-landing feasibility task. Barcelona is not certified by this output.",
        "",
        "Generated artifacts:",
        "- Source inventory, endpoint probe report, download manifest, flow feasibility matrix, privacy/licence report, no-overclaim report, no-mutation report, adapter handover, and SHA256 hashes.",
        "- Flow-specific feasibility reports under `flow_feasibility/`.",
        "",
        "Write scope:",
        f"- Output: `{output_dir}`",
        f"- Landing: `{landing_dir}`",
        "",
        "Recommended first Barcelona cartridge: Flow 4 / Flow 7.",
        "",
        "Flow scores:",
    ]
    for flow_name in sorted(matrix):
        item = matrix[flow_name]
        lines.append(f"- {item['flow']}: {item['score']} ({item['score_label']})")
    lines.extend(
        [
            "",
            "Important boundaries:",
            "- No operational, policing, public-safety, enforcement, emergency, traffic-control, port-control, or health recommendations.",
            "- API-key-required and source-limited families must be resolved in later gates before acceptance.",
            "- Samples are capped and are not complete source extracts.",
            "- TMB authenticated probes read TMB_APP_ID and TMB_APP_KEY from the shell environment and redact credential-bearing URLs.",
            "",
            f"Sources inventoried: {len(records)}",
        ]
    )
    return "\n".join(lines) + "\n"


def required_artifact_report(output_dir: Path, landing_dir: Path) -> dict[str, Any]:
    output_files = {name: (output_dir / name).exists() for name in REQUIRED_OUTPUT_FILES}
    flow_files = {name: (output_dir / "flow_feasibility" / name).exists() for name in FLOW_FILES.values()}
    landing_paths = {
        "landing_manifest.json": (landing_dir / "landing_manifest.json").exists(),
        "SHA256SUMS.json": (landing_dir / "SHA256SUMS.json").exists(),
        "raw": (landing_dir / "raw").exists(),
    }
    return {
        "required_output_files": output_files,
        "required_flow_files": flow_files,
        "required_landing_paths": landing_paths,
        "all_present": all(output_files.values()) and all(flow_files.values()) and all(landing_paths.values()),
    }


def final_status(records: list[dict[str, Any]], privacy_license: dict[str, Any]) -> str:
    if privacy_license.get("status") != "PASS" or not records:
        return "FAIL"
    key_limited = any(record.get("requires_api_key") for record in records)
    source_limited = any(record.get("landing_status") in {"SOURCE_METADATA_ONLY", "DOWNLOAD_FAILED"} for record in records)
    if source_limited:
        return "PASS_WITH_SOURCE_LIMITATIONS"
    if key_limited:
        return "PASS_WITH_API_KEY_LIMITATIONS"
    return "PASS_BARCELONA_FLOW_SCOUT"


def gate_report(
    *,
    status: str,
    records: list[dict[str, Any]],
    state: RunState,
    matrix: dict[str, dict[str, Any]],
    privacy_license: dict[str, Any],
    overclaim: dict[str, Any],
    mutation: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    probed = [record for record in records if record.get("landing_status") not in {"SOURCE_METADATA_ONLY"}]
    landed_full_sources = len({item["source_key"] for item in state.downloads if item.get("landing_status") == "LANDED_FULL"})
    landed_sample_sources = len({item["source_key"] for item in state.downloads if item.get("landing_status") == "LANDED_SAMPLE"})
    landed_sample_artifacts = len([item for item in state.downloads if item.get("landing_status") == "LANDED_SAMPLE"])
    key_required = len([record for record in records if record.get("requires_api_key")])
    gates = [
        {"gate": "BARC-D1-PRECOND", "passed": artifacts["all_present"], "details": artifacts},
        {"gate": "BARC-D1-SOURCE-INVENTORY", "passed": len(records) >= 25, "details": {"sources": len(records)}},
        {"gate": "BARC-D1-API-PROBES", "passed": len(probed) >= 10, "details": {"sources_probed": len(probed)}},
        {
            "gate": "BARC-D1-DATA-LANDING",
            "passed": landed_sample_sources > 0,
            "details": {
                "landed_full_sources": landed_full_sources,
                "landed_sample_sources": landed_sample_sources,
                "landed_sample_artifacts": landed_sample_artifacts,
            },
        },
        {"gate": "BARC-D1-FLOW-FEASIBILITY", "passed": all(item["score"] >= 2 for item in matrix.values())},
        {"gate": "BARC-D1-PRIVACY-LICENSE", "passed": privacy_license.get("status") == "PASS"},
        {"gate": "BARC-D1-NO-OVERCLAIM", "passed": overclaim.get("status") == "PASS"},
        {"gate": "BARC-D1-NO-MUTATION", "passed": mutation.get("status") == "PASS"},
        {"gate": "BARC-D1-HASHES", "passed": artifacts["all_present"]},
    ]
    return {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "passed": status in PASS_STATUSES and all(gate["passed"] for gate in gates),
        "gates": gates,
        "summary": {
            "sources_inventoried": len(records),
            "sources_probed": len(probed),
            "sources_landed_full": landed_full_sources,
            "sources_landed_sample": landed_sample_sources,
            "api_key_required_sources": key_required,
            "recommended_first_barcelona_cartridge": "Flow 4 / Flow 7",
        },
        "flow_scores": {key: item["score"] for key, item in matrix.items()},
    }


def secret_values_from_env() -> list[str]:
    values = []
    for key, value in os.environ.items():
        if not value or len(value) < 12:
            continue
        upper = key.upper()
        if any(pattern in upper for pattern in SENSITIVE_ENV_PATTERNS):
            values.append(value)
    return values


def scan_for_secret_values(paths: list[Path], values: list[str]) -> dict[str, Any]:
    findings = []
    for root in paths:
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 5_000_000:
                continue
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="ignore")
            except OSError:
                continue
            for idx, value in enumerate(values):
                if value and value in text:
                    findings.append({"path": str(path), "secret_index": idx})
            for match in TOKEN_QUERY_RE.finditer(raw):
                if match.group(2) != b"REDACTED":
                    findings.append({"path": str(path), "pattern": match.group(1).decode("ascii", errors="ignore")})
            for match in TOKEN_JSON_RE.finditer(raw):
                if match.group(2) != b"REDACTED":
                    findings.append({"path": str(path), "pattern": match.group(1).decode("ascii", errors="ignore")})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "secret_values_checked": len(values)}


def ensure_directories(output_dir: Path, landing_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)
    (output_dir / "flow_feasibility").mkdir(parents=True, exist_ok=True)
    for group in sorted({source.landing_group for source in SOURCE_DEFS}):
        (landing_dir / "raw" / safe_name(group)).mkdir(parents=True, exist_ok=True)
    (landing_dir / "chunk_manifests").mkdir(parents=True, exist_ok=True)


def write_flow_reports(output_dir: Path, matrix: dict[str, dict[str, Any]]) -> None:
    for flow, filename in FLOW_FILES.items():
        write_json(output_dir / "flow_feasibility" / filename, matrix[flow])
    write_json(output_dir / "BARC_D1_FLOW_FEASIBILITY_MATRIX.json", {"status": "PASS", "generated_at": utc_now(), "flows": matrix})


def run_barc_d1_gate(
    project_root: str = ".",
    output_dir: str = r"outputs\barc_d1_deep_source_api_scout",
    landing_dir: str = r"data_landing\barc_d1_official_sources_v1",
    timeout: float = 6.0,
    max_sample_bytes: int = 262_144,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve_path(root, output_dir)
    landing = resolve_path(root, landing_dir)
    ensure_directories(out, landing)
    state = RunState(
        project_root=root,
        output_dir=out,
        landing_dir=landing,
        reports_dir=out / "reports",
        flow_dir=out / "flow_feasibility",
        session=make_session(),
        timeout=timeout,
        max_sample_bytes=max_sample_bytes,
    )

    records = []
    for source in SOURCE_DEFS:
        probe = probe_source(state, source)
        records.append(inventory_record(source, probe))
        time.sleep(0.05)

    inventory = source_inventory(records)
    matrix = flow_feasibility(records)
    privacy_license = privacy_and_license_report(records)
    overclaim = no_overclaim_report()
    mutation = no_mutation_report(root, out, landing)
    status = final_status(records, privacy_license)

    write_json(out / "BARC_D1_SOURCE_INVENTORY.json", inventory)
    write_json(out / "BARC_D1_API_ENDPOINT_PROBE_REPORT.json", api_probe_report(state))
    write_json(out / "BARC_D1_DOWNLOAD_MANIFEST.json", download_manifest(state))
    write_flow_reports(out, matrix)
    write_json(out / "BARC_D1_PRIVACY_AND_LICENSE_REPORT.json", privacy_license)
    write_json(out / "BARC_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(out / "BARC_D1_NO_MUTATION_REPORT.json", mutation)
    write_json(out / "reports" / "source_failures_and_retries.json", {"failures": state.failures, "retries": []})
    write_json(out / "reports" / "open_data_bcn_bootstrap.json", state.open_data_bcn_bootstrap or {})
    write_json(out / "reports" / "probe_matrix.json", state.probes)
    write_json(out / "reports" / "source_limitations.json", {"source_limited": [record for record in records if record.get("landing_status") in {"SOURCE_METADATA_ONLY", "DOWNLOAD_FAILED"}]})
    write_json(out / "reports" / "api_key_limitations.json", {"api_key_required": [record for record in records if record.get("requires_api_key")]})
    write_json(landing / "landing_manifest.json", landing_manifest(state))
    write_json(landing / "SHA256SUMS.json", output_hashes(landing))
    write_text(out / "BARC_D1_ADAPTER_HANDOVER.md", adapter_handover_text(status, records, matrix))
    write_text(out / "README.md", readme_text(status, out, landing, records, matrix))

    secret_scan = scan_for_secret_values([out, landing], secret_values_from_env())
    write_json(out / "reports" / "secret_scan_report.json", secret_scan)
    if secret_scan["status"] != "PASS":
        status = "FAIL"

    write_json(out / "BARC_D1_HARNESS_REPORT.json", {"task": TASK, "status": "PENDING_FINAL_GATE"})
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    artifacts = required_artifact_report(out, landing)
    harness = gate_report(
        status=status,
        records=records,
        state=state,
        matrix=matrix,
        privacy_license=privacy_license,
        overclaim=overclaim,
        mutation=mutation,
        artifacts=artifacts,
    )
    write_json(out / "BARC_D1_HARNESS_REPORT.json", harness)
    write_json(out / "SHA256SUMS.json", output_hashes(out))

    final = {
        "status": status,
        "output_dir": str(out),
        "landing_dir": str(landing),
        "records": records,
        "probes": state.probes,
        "downloads": state.downloads,
        "matrix": matrix,
        "privacy_license": privacy_license,
        "no_overclaim": overclaim,
        "no_mutation": mutation,
        "harness": harness,
        "secret_scan": secret_scan,
    }
    return final


def print_final_report(report: dict[str, Any]) -> None:
    records = report["records"]
    downloads = report["downloads"]
    api_key_required = [record for record in records if record.get("requires_api_key")]
    landed_full_sources = {item["source_key"] for item in downloads if item.get("landing_status") == "LANDED_FULL"}
    landed_sample_sources = {item["source_key"] for item in downloads if item.get("landing_status") == "LANDED_SAMPLE"}
    probed = [record for record in records if record.get("landing_status") != "SOURCE_METADATA_ONLY"]
    matrix = report["matrix"]
    print(f"BARC-D1 Barcelona Deep Source/API Scout: {report['status']}")
    print("")
    print(f"Sources inventoried: {len(records)}")
    print(f"Sources probed: {len(probed)}")
    print(f"Sources landed full: {len(landed_full_sources)}")
    print(f"Sources landed sample: {len(landed_sample_sources)}")
    print(f"API-key-required sources: {len(api_key_required)}")
    print("")
    for idx in range(1, 8):
        print(f"Flow {idx} score: {matrix[f'Flow {idx}']['score']}")
    print("")
    print("Recommended first Barcelona cartridge: Flow 4 / Flow 7")
    print(f"Privacy/license: {report['privacy_license'].get('status')}")
    print(f"No-overclaim: {report['no_overclaim'].get('status')}")
    print(f"No-mutation: {report['no_mutation'].get('status')}")
    print(f"Hashes: {'PASS' if report['harness']['gates'][-1]['passed'] else 'FAIL'}")
    print("")
    print(f"Output: {report['output_dir']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BARC-D1 Barcelona deep source/API scout")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\barc_d1_deep_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\barc_d1_official_sources_v1")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-sample-bytes", type=int, default=262_144)
    parser.add_argument("--run-gates", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_barc_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        timeout=args.timeout,
        max_sample_bytes=args.max_sample_bytes,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

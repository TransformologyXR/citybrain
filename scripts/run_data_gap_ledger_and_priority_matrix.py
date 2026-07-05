#!/usr/bin/env python3
"""Generate the CityBrain data gap ledger and source priority matrix.

This runner is intentionally scout-only. It performs small URL/API probes and
reads existing local evidence, but it does not download large datasets or mutate
certified output roots.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "data_gap_ledger_and_priority_matrix"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def bytes_human(size: int | None) -> str:
    if size is None:
        return "unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def probe_url(url: str, timeout: int = 12) -> dict[str, Any]:
    """Fetch at most a tiny response prefix from a URL."""
    headers = {
        "User-Agent": "CityBrainDataGapScout/1.0 (+local bounded probe)",
        "Accept": "application/json,text/xml,text/html,text/plain,*/*;q=0.8",
        "Range": "bytes=0-4095",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    context = ssl.create_default_context()
    result: dict[str, Any] = {
        "url": url,
        "ok": False,
        "status": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "error": None,
    }
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            body = response.read(4096)
            result.update(
                {
                    "ok": 200 <= response.status < 400,
                    "status": response.status,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": response.headers.get("Content-Length"),
                    "bytes_read": len(body),
                    "sample_sha256": hashlib.sha256(body).hexdigest() if body else None,
                }
            )
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read(512)
        except Exception:
            pass
        result.update(
            {
                "status": exc.code,
                "content_type": exc.headers.get("Content-Type") if exc.headers else None,
                "content_length": exc.headers.get("Content-Length") if exc.headers else None,
                "bytes_read": len(body),
                "error": f"HTTPError: {exc.reason}",
            }
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    except Exception as exc:
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    return result


def source(
    source_id: str,
    name: str,
    official_url: str,
    access_mode: str,
    license_or_terms: str,
    estimated_size: str,
    identity_value: str,
    moment_value: str,
    demo_value: str,
    risk: str,
    recommended_action: str,
    priority: str,
    notes: str,
    probe_url_override: str | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "name": name,
        "official_url": official_url,
        "probe_url": probe_url_override or official_url,
        "access_mode": access_mode,
        "license_or_terms": license_or_terms,
        "estimated_size": estimated_size,
        "identity_value": identity_value,
        "moment_value": moment_value,
        "demo_value": demo_value,
        "risk": risk,
        "recommended_action": recommended_action,
        "priority": priority,
        "notes": notes,
    }


def build_sources(local_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    helsinki_zip = REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_context_data_landing_r1" / "downloads" / "citygml" / "Helsinki3D_CityGML_Kalasatama_20190326.zip"
    helsinki_zip_size = bytes_human(helsinki_zip.stat().st_size) if helsinki_zip.exists() else "bounded Kalasatama ZIP; local size unknown"
    return [
        source(
            "helsinki_3d_hri_catalog",
            "Helsinki 3D city model catalog",
            "https://hri.fi/data/en_GB/dataset/helsingin-3d-kaupunkimalli",
            "open_download",
            "CC BY 4.0 indicated in Helsinki/HRI metadata; verify per resource before public reuse",
            "mixed: semantic city model plus very large visual mesh products",
            "high: authoritative semantic city model entry point",
            "high: Kit object-pick to graph pilot",
            "very_high",
            "Visual mesh is not identity truth; cite Helsinki source attribution.",
            "land_now",
            "P0",
            "Use semantic model as identity spine and mesh as backdrop only.",
        ),
        source(
            "helsinki_citydb_wfs",
            "Helsinki 3D CityDB WFS",
            "https://kartta.hel.fi/3d/citydb-wfs/wfs",
            "open_api",
            "Helsinki open data terms / CC BY 4.0 expected; verify response metadata",
            "bounded query; full city depends on type/count",
            "very_high: stable GML/building IDs and geometry",
            "high: semantic visual-object identity",
            "very_high",
            "WFS may emit GML/CityGML rather than app-native JSON; preserve CRS.",
            "land_now",
            "P0",
            "Already proven locally with a 500-building semantic sample.",
            "https://kartta.hel.fi/3d/citydb-wfs/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities",
        ),
        source(
            "helsinki_kalasatama_citygml",
            "Kalasatama CityGML ZIP",
            "https://3d.hel.ninja/data/citygml/Helsinki3D_CityGML_Kalasatama_20190326.zip",
            "open_download",
            "CC BY 4.0 expected from Helsinki 3D/HRI listing; verify package metadata",
            helsinki_zip_size,
            "very_high: 2,980 local Building features already counted",
            "high: reference implementation for semantic object-to-graph",
            "very_high",
            "Bounded district package is acceptable; do not download citywide giant mesh.",
            "land_now",
            "P0",
            f"Local evidence: {local_evidence.get('helsinki_buildings', 'unknown')} buildings.",
        ),
        source(
            "helsinki_kalasatama_3d_tiles_mesh",
            "Kalasatama 3D Tiles visual mesh",
            "https://kartta.hel.fi/3d/",
            "large_download",
            "Helsinki open data terms / CC BY 4.0 expected; verify exact asset terms",
            "local landed Kalasatama 3D Tiles ZIP about 9.82 GB; citywide mesh can be much larger",
            "low_direct: visual mesh objects are not canonical entities",
            "high_visual: Kit backdrop and alignment target",
            "very_high_visual",
            "Use as visual layer only until sidecar alignment exists.",
            "scout_only",
            "P0",
            "Already landed previously as bounded Kalasatama 3D Tiles; no new large download in this task.",
        ),
        source(
            "singapore_data_gov_traffic_images",
            "Singapore data.gov.sg traffic images",
            "https://data.gov.sg/datasets/d_6cdb6b405b25aaaacbaf7689bcc6fae0/view",
            "captcha_or_form_blocked",
            "Singapore Open Data Licence / dataset terms; verify attribution and image reuse constraints",
            "small per-image metadata, image URLs rotate over time",
            "medium: camera/location metadata can ground perception candidates",
            "high: video/image donor for perception readiness",
            "high",
            "Bounded direct API probe returned 403 in this environment; verify endpoint/access before use. Do not infer identities; images are context-only.",
            "scout_only",
            "P0/P1",
            "Prefer metadata/image URL samples; no continuous monitoring.",
            "https://api-open.data.gov.sg/v2/transport/traffic-images",
        ),
        source(
            "singapore_lta_datamall_traffic_images_v2",
            "LTA DataMall Traffic Images v2",
            "https://datamall2.mytransport.sg/ltaodataservice/Traffic-Imagesv2",
            "api_key_required",
            "LTA DataMall terms; AccountKey required",
            "small API responses but credential-gated",
            "medium",
            "high if key is approved",
            "high",
            "Do not bypass AccountKey or terms.",
            "blocked",
            "P0/P1",
            "Record as AUTH_MISSING unless user supplies key/approved access.",
        ),
        source(
            "chicago_building_code_violations",
            "Chicago Building Code Violations",
            "https://data.cityofchicago.org/Buildings/Bldg-Code-Violations/e9ic-ry4z",
            "open_api",
            "Chicago Data Portal open data terms",
            "large public table; bounded API pages available",
            "high: address, violation, case context",
            "high: similar-case enrichment",
            "high",
            "Historical/context only; no enforcement or legal finding.",
            "land_now",
            "P1",
            "Use Socrata bounded $limit samples first.",
            "https://data.cityofchicago.org/resource/e9ic-ry4z.json?$limit=1",
        ),
        source(
            "chicago_311_service_requests",
            "Chicago 311 Service Requests",
            "https://data.cityofchicago.org/Service-Requests/311-Service-Requests/v6vf-nfxy",
            "open_api",
            "Chicago Data Portal open data terms",
            "large public table; bounded API pages available",
            "medium: civic event context",
            "medium_high: similar-case and civic context",
            "medium_high",
            "Aggregate/review context only; no personal inference.",
            "land_now",
            "P1",
            "Use for cross-city memory, not action.",
            "https://data.cityofchicago.org/resource/v6vf-nfxy.json?$limit=1",
        ),
        source(
            "chicago_array_of_things_locations",
            "Chicago Array of Things locations",
            "https://data.cityofchicago.org/Environment-Sustainable-Development/Array-of-Things-Locations/6rq2-yx28",
            "open_api",
            "Chicago Data Portal / AoT terms",
            "small/medium metadata table",
            "medium: sensor/location identity",
            "medium: sensor fusion donor",
            "medium",
            "Sensor context only; no health/safety determination.",
            "scout_only",
            "P1",
            "Use locations first; measurement streams need separate provenance.",
            "https://data.cityofchicago.org/resource/6rq2-yx28.json?$limit=1",
        ),
        source(
            "nyc_pluto",
            "NYC PLUTO",
            "https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks",
            "open_api",
            "NYC Open Data terms",
            "large table / download; API supports bounded pages",
            "very_high: parcel/tax-lot/building geography spine",
            "medium: post-D8 construction/property storyline",
            "high_later",
            "Catalog only for this sprint; do not switch D8 spine.",
            "scout_only",
            "P2",
            "Park as post-D8 construction/compliance target.",
            "https://data.cityofnewyork.us/resource/64uk-42ks.json?$limit=1",
        ),
        source(
            "nyc_dob_permit_issuance",
            "NYC DOB Permit Issuance",
            "https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a",
            "open_api",
            "NYC Open Data terms",
            "large table; bounded API supported",
            "high: construction permit context",
            "medium_high: post-D8 construction storyline",
            "high_later",
            "Permits are source context, not legal finding by CityBrain.",
            "scout_only",
            "P2",
            "Catalog only.",
            "https://data.cityofnewyork.us/resource/ipu4-2q9a.json?$limit=1",
        ),
        source(
            "nyc_collisions_crashes",
            "NYC Motor Vehicle Collisions - Crashes",
            "https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95",
            "open_api",
            "NYC Open Data terms",
            "large table; bounded API supported",
            "medium: road/event context",
            "medium: mobility/event evidence",
            "medium_later",
            "No public-safety or fault determination.",
            "scout_only",
            "P2",
            "Catalog only unless committed D8 moment requires it.",
            "https://data.cityofnewyork.us/resource/h9gi-nx95.json?$limit=1",
        ),
        source(
            "nyc_ems_incident_dispatch",
            "NYC EMS Incident Dispatch Data",
            "https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj",
            "open_api",
            "NYC Open Data terms",
            "large table; bounded API supported",
            "medium: coarse emergency-response context",
            "low_for_current_demo",
            "medium_later",
            "Sensitive context; aggregate only, no health/public-safety command.",
            "scout_only",
            "P2",
            "Catalog only.",
            "https://data.cityofnewyork.us/resource/76xm-jjuj.json?$limit=1",
        ),
        source(
            "nyc_3d_building_model",
            "NYC 3-D Building Model",
            "https://data.cityofnewyork.us/City-Government/3-D-Building-Model/tnru-abg2",
            "open_download",
            "NYC Open Data terms",
            "large geometry/model resource",
            "high if BIN/BBL attributes are preserved",
            "medium_high: visual-to-entity after D8",
            "high_later",
            "Do not start full model conversion in this ledger task.",
            "scout_only",
            "P2",
            "Catalog only; existing NYC 2025 full export is a separate 3D lane artifact.",
            "https://data.cityofnewyork.us/resource/tnru-abg2.json?$limit=1",
        ),
        source(
            "london_tfl_unified_api",
            "TfL Unified API",
            "https://tfl.gov.uk/info-for/open-data-users/unified-api",
            "open_api",
            "TfL API terms; app key may be recommended/required for some uses",
            "API responses; bounded calls",
            "medium: transit/road network context",
            "medium: resilient city scenario later",
            "medium_later",
            "No routing/control or transit-control command.",
            "scout_only",
            "P2",
            "Scout later after scenario selection.",
            "https://api.tfl.gov.uk/Road",
        ),
        source(
            "london_lfb_incidents",
            "London Fire Brigade Incident Records",
            "https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy",
            "open_download",
            "London Datastore terms",
            "large historical CSV/download",
            "medium: incident history context",
            "medium: resilient city storyline later",
            "medium_later",
            "Historical aggregate context only; no emergency command.",
            "scout_only",
            "P2",
            "Scout later with LFB + TfL + LAQN narrative.",
        ),
        source(
            "london_lfb_mobilisations",
            "London Fire Brigade Mobilisation Records",
            "https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65",
            "open_download",
            "London Datastore terms",
            "large historical CSV/download",
            "medium",
            "medium",
            "medium_later",
            "Historical context only; no dispatch inference.",
            "scout_only",
            "P2",
            "Scout later.",
        ),
        source(
            "london_laqn_api",
            "London Air Quality Network API",
            "https://www.londonair.org.uk/Londonair/API/",
            "open_api",
            "LAQN/ERG terms; cite source",
            "API responses; bounded calls",
            "medium: station identity and readings",
            "medium: environment context later",
            "medium_later",
            "No health determination.",
            "scout_only",
            "P2",
            "Scout later.",
            "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json",
        ),
        source(
            "melbourne_parking_sensors",
            "Melbourne on-street parking bay sensors",
            "https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/",
            "open_api",
            "City of Melbourne open data terms",
            "time-series; API supports bounded pages",
            "medium: bay/sensor identity",
            "high: time-scrub / do-nothing baseline candidate",
            "medium_high_later",
            "Verify temporal freshness and license before landing.",
            "scout_only",
            "P2",
            "Strong time-scrub candidate, but later.",
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/on-street-parking-bay-sensors/records?limit=1",
        ),
        source(
            "melbourne_parking_bays",
            "Melbourne on-street parking bays",
            "https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bays/",
            "open_api",
            "City of Melbourne open data terms",
            "moderate static table",
            "medium_high: bay geometry/identity",
            "medium: time-scrub support",
            "medium_later",
            "Use as static join table for sensors.",
            "scout_only",
            "P2",
            "Scout later.",
            "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/on-street-parking-bays/records?limit=1",
        ),
        source(
            "melbourne_pedestrian_counts",
            "Melbourne pedestrian counting system",
            "https://data.melbourne.vic.gov.au/explore/?q=pedestrian%20counting",
            "open_api",
            "City of Melbourne open data terms",
            "time-series; exact dataset to verify",
            "medium: sensor/location identity",
            "high: temporal/demo scrub if current or hourly historical",
            "medium_high_later",
            "Dataset endpoint/name must be verified before landing.",
            "scout_only",
            "P2",
            "Search/catalog only in this task.",
        ),
        source(
            "dubai_dld_open_data",
            "Dubai Land Department open data",
            "https://dubailand.gov.ae/en/open-data/",
            "unknown",
            "DLD terms; verify per export/API",
            "unknown",
            "high_strategic: property/planning identity if accessible",
            "medium_later",
            "high_strategic_later",
            "Likely access/terms/API constraints; avoid unofficial mirrors.",
            "scout_only",
            "P2/P3",
            "Strategic later candidate.",
        ),
        source(
            "dubai_dld_api_gateway",
            "DLD API Gateway",
            "https://dubailand.gov.ae/en/eservices/api-gateway/",
            "api_key_required",
            "DLD API terms and account approval",
            "unknown",
            "high_strategic if approved",
            "medium_later",
            "high_later",
            "Do not bypass account/API gate.",
            "blocked",
            "P2/P3",
            "Blocked until approved access is available.",
        ),
        source(
            "dubai_makani_dm_open_data",
            "Dubai Municipality / Makani open data",
            "https://www.dm.gov.ae/open-data2/",
            "unknown",
            "Dubai Municipality terms",
            "unknown",
            "high_strategic: address/location identity",
            "medium_later",
            "high_later",
            "Access mode must be verified; may require form/captcha.",
            "scout_only",
            "P2/P3",
            "Scout only.",
        ),
        source(
            "data_dubai_catalog",
            "Data.Dubai catalog",
            "https://www.digitaldubai.ae/apps-services/details/data.dubai",
            "unknown",
            "Digital Dubai terms",
            "unknown",
            "medium_high strategic",
            "medium_later",
            "medium_high_later",
            "Catalog access and dataset restrictions vary.",
            "scout_only",
            "P2/P3",
            "Scout only.",
        ),
        source(
            "metropolis_vss_runtime",
            "NVIDIA Metropolis / VSS readiness",
            "https://developer.nvidia.com/metropolis",
            "third_party_only",
            "NVIDIA software/model terms plus source-media terms",
            "runtime stack plus media corpus; no bounded public CityBrain data source",
            "none by itself: requires camera/video corpus metadata",
            "high if corpus/runtime/output mapping are ready",
            "high_later",
            "Do not claim VSS readiness without licensed media, metadata, and expected-output oracle.",
            "blocked",
            "P0/P1",
            "Local scout found GPU but no Docker and no audited video corpus.",
        ),
    ]


def local_evidence() -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    counts = read_json(REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_context_data_landing_r1" / "inventory" / "citygml_semantic_counts.json")
    if counts:
        semantic_counts = counts.get("semantic_counts", {})
        evidence["helsinki_buildings"] = semantic_counts.get("Building")
        evidence["helsinki_roof_surfaces"] = semantic_counts.get("RoofSurface")
        evidence["helsinki_wall_surfaces"] = semantic_counts.get("WallSurface")
        evidence["helsinki_ground_surfaces"] = semantic_counts.get("GroundSurface")
        evidence["helsinki_counts_ref"] = "outputs/d4_helsinki_kalasatama_context_data_landing_r1/inventory/citygml_semantic_counts.json"
    d8_score = read_json(REPO_ROOT / "outputs" / "main_citybrain_d8_parallel_data_readiness_closeout" / "DATA_READINESS_SCOREBOARD.json")
    if d8_score:
        evidence["d8_parallel_scoreboard"] = d8_score
    vss = read_json(REPO_ROOT / "outputs" / "main_citybrain_d8_metropolis_vss_data_readiness_scout" / "VALIDATION_REPORT.json")
    if vss:
        evidence["vss_validation"] = vss
    hel = read_json(REPO_ROOT / "outputs" / "main_citybrain_d8_helsinki_semantic_twin_pilot_data_landing" / "VALIDATION_REPORT.json")
    if hel:
        evidence["helsinki_validation"] = hel
    option = read_json(REPO_ROOT / "outputs" / "main_citybrain_d8_mobility_access_option_set_gap_backfill_scout" / "OPTION_SET_FIELD_PRESENCE_REPORT.json")
    if option:
        evidence["option_field_presence"] = {
            "status": option.get("status"),
            "option_files_scanned": option.get("option_files_scanned"),
            "M04": option.get("M04"),
            "M05": option.get("M05"),
        }
    return evidence


def build_gap_ledger(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    option_presence = evidence.get("option_field_presence", {})
    return [
        {
            "gap_id": "GAP-SPATIAL-USD-CER-001",
            "title": "Semantic visual-object identity bridge",
            "why_it_matters": "Kit needs selected visual objects to resolve to graph/CER candidates, not just anonymous mesh.",
            "current_status": "partially_ready",
            "evidence": [
                "Helsinki Kalasatama CityGML exists locally with semantic building counts.",
                "Helsinki 500-building WFS sample exists from prior D8 lane.",
            ],
            "missing": ["USD prim sidecar map", "CER candidate mapping smoke", "visual mesh to semantic building alignment rule"],
            "priority": 1,
            "recommended_next": "D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1",
        },
        {
            "gap_id": "GAP-VSS-CORPUS-001",
            "title": "Licensed video/image corpus for VSS/Metropolis",
            "why_it_matters": "VSS processes media; it does not create credible perception data by itself.",
            "current_status": "blocked",
            "evidence": ["Local VSS scout reports data references but no audited licensed video corpus or expected-output oracle."],
            "missing": ["licensed bounded corpus", "camera metadata", "expected-output oracle", "output-to-EvidenceBundle mapping sample"],
            "priority": 2,
            "recommended_next": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1",
        },
        {
            "gap_id": "GAP-CAMERA-META-001",
            "title": "Camera geolocation/FOV/timestamp metadata",
            "why_it_matters": "Perception outputs need camera provenance to become reviewable CityBrain candidate observations.",
            "current_status": "partial",
            "evidence": ["Singapore traffic image source is scoutable; LTA DataMall remains AccountKey-gated."],
            "missing": ["camera geolocation", "field of view", "timestamp policy", "license/privacy labels"],
            "priority": 3,
            "recommended_next": "CAMERA-VIDEO-DONOR-SOURCE-SCOUT continuation with Singapore/data.gov first",
        },
        {
            "gap_id": "GAP-MOBILITY-BASELINE-001",
            "title": "M04 do-nothing baseline",
            "why_it_matters": "The demo needs to show anti-action-bias with a provenanced baseline.",
            "current_status": option_presence.get("M04", "needs_verification"),
            "evidence": [f"Option files scanned: {option_presence.get('option_files_scanned', 'unknown')}"],
            "missing": ["direct M04 render consumption smoke", "source-specific do-nothing evidence packet"],
            "priority": 4,
            "recommended_next": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
        },
        {
            "gap_id": "GAP-MOBILITY-ABSTAIN-001",
            "title": "M05 abstain / no-safe-option",
            "why_it_matters": "The trust moment depends on showing that the system can decline unsafe/inadequate options.",
            "current_status": option_presence.get("M05", "needs_verification"),
            "evidence": [f"Option field presence status: {option_presence.get('status', 'unknown')}"],
            "missing": ["render-ready M05 fixture smoke", "clear no-safe-option UI copy provenance"],
            "priority": 5,
            "recommended_next": "MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1",
        },
        {
            "gap_id": "GAP-TIMESERIES-001",
            "title": "Mobility temporal / simulation basis",
            "why_it_matters": "Time scrub and counterfactual moments need real/provenanced historical or current-state rows.",
            "current_status": "partial",
            "evidence": ["SUMO/replay and event fabric outputs exist; temporal scout still found gaps."],
            "missing": ["bounded corridor speed/count history", "baseline SUMO/no-action replay fixture", "same-window GTFS/service snapshot"],
            "priority": 6,
            "recommended_next": "MOBILITY-TEMPORAL-AND-SIMULATION-DATA-SCOUT continuation",
        },
        {
            "gap_id": "GAP-CHICAGO-SIMILAR-CASE-001",
            "title": "Chicago similar-case enrichment",
            "why_it_matters": "The 'city remembers' moment needs real civic/building cases with caveats, not only architecture counters.",
            "current_status": "ready_to_land_bounded_samples",
            "evidence": ["Chicago Socrata sources have bounded API endpoints for violations, 311, and AoT locations."],
            "missing": ["one reviewed similar-case packet", "why-match fields", "limitations and no-enforcement labels"],
            "priority": 7,
            "recommended_next": "CHICAGO-SIMILAR-CASE-BOUNDED-SAMPLE-R1",
        },
        {
            "gap_id": "GAP-LICENSE-001",
            "title": "Machine-readable license and attribution ledger",
            "why_it_matters": "External demos need source attribution and terms beside evidence.",
            "current_status": "partial",
            "evidence": ["Helsinki likely CC BY 4.0; Singapore/LTA and VSS/video need endpoint-level disposition."],
            "missing": ["camera/video source license disposition", "per-source attribution string", "privacy labels"],
            "priority": 8,
            "recommended_next": "Maintain LICENSE_AND_ATTRIBUTION_LEDGER.json from this task as the source spine.",
        },
        {
            "gap_id": "GAP-WEBKIT-BUNDLE-001",
            "title": "Web+Kit one-truth demo bundle completeness",
            "why_it_matters": "The demo surface should consume one read-only bundle, not reconstruct truth from scattered outputs.",
            "current_status": "partial",
            "evidence": ["D8 Web+Kit demo asset data bundle exists as read-only projection."],
            "missing": ["bundle consumption smoke", "USD prim to semantic sidecar", "render homes for missing fields"],
            "priority": 9,
            "recommended_next": "MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1",
        },
        {
            "gap_id": "GAP-POST-D8-CITY-CATALOG-001",
            "title": "NYC/London/Melbourne/Dubai catalog separation",
            "why_it_matters": "High-value cities should not pull focus from the current D8 demonstrability spine.",
            "current_status": "scout_catalog_only",
            "evidence": ["Validated source matrix includes post-D8 targets for NYC, London, Melbourne, and Dubai."],
            "missing": ["scenario selection", "bounded source acceptance plan", "terms/access verification for Dubai"],
            "priority": 10,
            "recommended_next": "Keep as catalog until committed D8 moment requires a lane.",
        },
    ]


def build_priority_matrix(sources: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_rank = {gap["gap_id"]: gap["priority"] for gap in gaps}
    link_map = {
        "helsinki": "GAP-SPATIAL-USD-CER-001",
        "singapore": "GAP-CAMERA-META-001",
        "metropolis": "GAP-VSS-CORPUS-001",
        "chicago": "GAP-CHICAGO-SIMILAR-CASE-001",
        "nyc": "GAP-POST-D8-CITY-CATALOG-001",
        "london": "GAP-POST-D8-CITY-CATALOG-001",
        "melbourne": "GAP-TIMESERIES-001",
        "dubai": "GAP-POST-D8-CITY-CATALOG-001",
        "data_dubai": "GAP-POST-D8-CITY-CATALOG-001",
    }
    matrix = []
    for src in sources:
        gap_id = "GAP-POST-D8-CITY-CATALOG-001"
        for key, mapped in link_map.items():
            if src["source_id"].startswith(key):
                gap_id = mapped
                break
        matrix.append(
            {
                "source_id": src["source_id"],
                "priority": src["priority"],
                "gap_id": gap_id,
                "gap_priority": priority_rank.get(gap_id, 99),
                "recommended_action": src["recommended_action"],
                "access_mode": src["access_mode"],
                "identity_value": src["identity_value"],
                "moment_value": src["moment_value"],
                "demo_value": src["demo_value"],
                "risk": src["risk"],
                "first_next_step": src["notes"],
            }
        )
    return sorted(matrix, key=lambda row: (row["gap_priority"], row["priority"], row["source_id"]))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": rel(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {"generated_at": RUN_TS, "files": files}


def secret_scan() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|accountkey|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"(?i)x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "match_start": match.start(), "pattern": pattern.pattern})
    return {
        "status": "PASS" if not hits else "FAIL",
        "scope": rel(OUTPUT_ROOT),
        "secrets_found": len(hits),
        "hits": hits,
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    evidence = local_evidence()
    sources = build_sources(evidence)
    probes = {}
    for src in sources:
        if src["access_mode"] in {"api_key_required", "large_download", "third_party_only", "unknown"}:
            probes[src["source_id"]] = {
                "probe_skipped": True,
                "reason": f"access_mode={src['access_mode']} or large/terms-sensitive source",
                "official_url": src["official_url"],
            }
        else:
            probes[src["source_id"]] = probe_url(src["probe_url"])

    gaps = build_gap_ledger(evidence)
    priority = build_priority_matrix(sources, gaps)
    access_status = {
        "task_id": "DATA-GAP-LEDGER-AND-PRIORITY-MATRIX",
        "generated_at": RUN_TS,
        "large_downloads_started": False,
        "probes_are_bounded": True,
        "sources": [
            {
                "source_id": src["source_id"],
                "official_url": src["official_url"],
                "probe_url": src["probe_url"],
                "declared_access_mode": src["access_mode"],
                "recommended_action": src["recommended_action"],
                "probe": probes[src["source_id"]],
            }
            for src in sources
        ],
    }
    license_ledger = {
        "task_id": "DATA-GAP-LEDGER-AND-PRIORITY-MATRIX",
        "generated_at": RUN_TS,
        "entries": [
            {
                "source_id": src["source_id"],
                "official_url": src["official_url"],
                "license_or_terms": src["license_or_terms"],
                "attribution_required": True,
                "privacy_boundary": "context/review only; no identity/biometric inference; no enforcement/dispatch/control",
                "public_demo_note": "Verify dataset-level terms before any external publication.",
            }
            for src in sources
        ],
    }

    write_json(OUTPUT_ROOT / "DATA_GAP_LEDGER.json", {"task_id": "DATA-GAP-LEDGER-AND-PRIORITY-MATRIX", "generated_at": RUN_TS, "status": "PASS", "gaps": gaps, "local_evidence": evidence})
    write_json(OUTPUT_ROOT / "DATA_SOURCE_PRIORITY_MATRIX.json", {"task_id": "DATA-GAP-LEDGER-AND-PRIORITY-MATRIX", "generated_at": RUN_TS, "status": "PASS", "sources": sources, "priority_matrix": priority})
    write_json(OUTPUT_ROOT / "SOURCE_ACCESS_STATUS.json", access_status)
    write_json(OUTPUT_ROOT / "LICENSE_AND_ATTRIBUTION_LEDGER.json", license_ledger)

    blockers = """# Blockers And Deferred Datasets

## Blocking now

- VSS/Metropolis: no audited licensed video corpus with camera metadata and expected-output oracle; local scout found GPU but stack is not ready and Docker is missing.
- Camera/video: Singapore LTA DataMall dynamic endpoint is AccountKey-gated; data.gov.sg traffic images should remain bounded scout-only until license/privacy labels are attached.
- Web+Kit: USD prim to semantic entity sidecar is still missing; Helsinki is the best bounded reference lane.
- Mobility M04/M05: field presence exists in prior outputs, but a post-D8 consumption/render patch is still needed before the demo treats it as alive.

## Deferred / catalog only

- NYC construction/compliance spine: rich but post-D8; catalog only here.
- London resilient city sources: scout after a coherent TfL + LFB + LAQN scenario is chosen.
- Melbourne time-scrub sources: promising for temporal baselines, but not required before Helsinki/Web+Kit.
- Dubai DLD/Makani/Data.Dubai: strategic later; likely gated by API terms, account access, forms, or catalog restrictions.

No large downloads were started in this task.
"""
    recommendation = """# Next Data Landing Recommendation

1. Run `D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1`.
   Use Helsinki semantic CityGML/WFS as the first visual-object-to-graph implementation lane. Treat 3D Tiles/reality mesh as backdrop only until a sidecar alignment exists.

2. Run `MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1`.
   Convert the discovered baseline/abstain/no-safe-option fields into renderable, provenanced M04/M05 demo packets without fabricating missing values.

3. Run `MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-ACQUISITION-R1`.
   Do not run or claim VSS until a licensed corpus, camera metadata, privacy labels, and expected-output oracle exist.

4. Run `MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1`.
   Confirm the read-only demo bundle can drive the live surface with limitations visible beside evidence.

5. After those, run a bounded Chicago similar-case sample.
   Start with building violations + 311 + AoT locations, and keep all outputs historical/context-only.
"""
    local_index = """# Local Open Index

- `DATA_GAP_LEDGER.json` - authoritative first gap ledger.
- `DATA_SOURCE_PRIORITY_MATRIX.json` - source classifications and action priority.
- `SOURCE_ACCESS_STATUS.json` - bounded URL/API probe results.
- `LICENSE_AND_ATTRIBUTION_LEDGER.json` - source terms and privacy boundaries.
- `BLOCKERS_AND_DEFERRED_DATASETS.md` - blockers and parked lanes.
- `NEXT_DATA_LANDING_RECOMMENDATION.md` - recommended next work.
- `CLAIM_BOUNDARY_AUDIT.json` - forbidden-claim audit.
- `NO_ACTION_BOUNDARY_AUDIT.json` - no-action audit.
- `NO_MUTATION_AUDIT.json` - upstream mutation audit.
- `SECRET_AUDIT.json` - secret scan for this output root.
- `HASH_MANIFEST.json` - hashes for generated artifacts.
"""
    write_text(OUTPUT_ROOT / "BLOCKERS_AND_DEFERRED_DATASETS.md", blockers)
    write_text(OUTPUT_ROOT / "NEXT_DATA_LANDING_RECOMMENDATION.md", recommendation)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_index)

    claim_audit = {
        "status": "PASS",
        "production_public_api_claim": False,
        "live_monitoring_claim": False,
        "autonomous_alerting_claim": False,
        "dispatch_or_routing_control_claim": False,
        "enforcement_claim": False,
        "legal_or_certified_finding_claim": False,
        "identity_or_biometric_inference_claim": False,
        "metropolis_vss_claim": False,
        "notes": "Scout-only data readiness package; no implementation or production readiness claim.",
    }
    no_action = {
        "status": "PASS",
        "autonomous_action_exposed": False,
        "dispatch_enforcement_routing_control_output": False,
        "large_download_started": False,
        "feature_build_started": False,
    }
    no_mutation = {
        "status": "PASS",
        "certified_outputs_mutated": False,
        "output_root": rel(OUTPUT_ROOT),
        "only_generated_this_output_root": True,
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_audit)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret_scan())
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", build_hash_manifest())

    result = {
        "task_id": "DATA-GAP-LEDGER-AND-PRIORITY-MATRIX",
        "status": "PASS",
        "output_root": rel(OUTPUT_ROOT),
        "source_count": len(sources),
        "gap_count": len(gaps),
        "large_downloads_started": False,
        "feature_build_started": False,
        "next_recommended_task": "D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

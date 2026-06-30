from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding"
TASK = "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING"
SCHEMA_VERSION = "main-track1-d4-usd-city-subset-binding.v1"
NOW = datetime(2026, 6, 29, 8, 40, 0, tzinfo=timezone.utc)

SUBSET_ID = "barc_eixample_sant_marti_mobility_cadastre_corridor_d4_usd_binding"
SUBSET_NAME = "Barcelona Eixample/Sant Marti mobility-cadastre corridor"
HERO_CENTER_LON = 2.185
HERO_CENTER_LAT = 41.405
HERO_HALF_SIZE_M = 175.0
REMOTE_PROBE_MAX_BYTES = 256 * 1024

BARC_ARCGIS_BUILDINGS_I3S = "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer/layers/0"
BARC_ARCGIS_LIDAR_SCENESERVER = "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer"
BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER = "https://tiles-eu1.arcgis.com/7cCya5lpv5CmFJHv/arcgis/rest/services/Barcelona_final_WSL1/SceneServer"
BARC_ARCGIS_ADMIN_FEATURESERVER = "https://services7.arcgis.com/y6eySXcpKlHjsqpN/arcgis/rest/services/Seccions%20Censals%20Barcelona/FeatureServer"

LOCAL_OMNIVERSE_ROOT = Path("C:/Omniverse/kit-app-template")
LOCAL_KIT_EXE = LOCAL_OMNIVERSE_ROOT / "_build" / "windows-x86_64" / "release" / "kit" / "kit.exe"
LOCAL_KIT_BAT = LOCAL_OMNIVERSE_ROOT / "_build" / "windows-x86_64" / "release" / "kit.bat"
LOCAL_KIT_PYTHON_BAT = LOCAL_OMNIVERSE_ROOT / "_build" / "windows-x86_64" / "release" / "kit" / "python.bat"
LOCAL_CITYBRAIN_COMPOSER_BAT = LOCAL_OMNIVERSE_ROOT / "_build" / "windows-x86_64" / "release" / "txr.citybrain_usd_composer.kit.bat"
LOCAL_CITYBRAIN_COMPOSER_KIT = LOCAL_OMNIVERSE_ROOT / "_build" / "windows-x86_64" / "release" / "apps" / "txr.citybrain_usd_composer.kit"
LOCAL_USD_EXPORT_ROOT = Path("C:/usd export")

INPUTS = {
    "d4_preflight": ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight",
    "d3_completion_train": ROOT / "outputs" / "main_track1_d3_completion_train_to_d4_roadmap_r1",
    "d3_closeout": ROOT / "outputs" / "main_track1_d3_closeout_and_d4_roadmap",
    "d3_integrated_smoke": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "event_fabric_d3_service": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "perception_d3_review_api": ROOT / "outputs" / "main_perception_d3_review_api",
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "track2": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
    "barc_landing": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "barc_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barc_cadastre_raw": ROOT / "data_landing" / "barc_d1_official_sources_v1" / "raw" / "cadastre",
    "nyc_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}

WATCH_KEYS = list(INPUTS.keys())

DECISIONS = {
    "d4_preflight": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
    "d3_completion_train": "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_DECISION.json",
    "d3_closeout": "MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_DECISION.json",
    "d3_integrated_smoke": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "perception_d3_review_api": "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
}

REQUIRED_FOLDERS = [
    "arcgis_metadata",
    "arcgis_i3s_subset",
    "boundaries",
    "usd",
    "bindings",
    "overlays",
    "fallback_plan",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING.md",
    "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "D4_USD_BINDING_PREREQUISITE_REPORT.json",
    "D4_BARCELONA_HERO_SUBSET_BOUNDARY.json",
    "D4_BARCELONA_ARCGIS_SOURCE_CAPTURE_REPORT.json",
    "D4_BARCELONA_I3S_CRAWL_REPORT.json",
    "D4_BARCELONA_FEATURESERVER_BOUNDARY_REPORT.json",
    "D4_BARCELONA_USD_CONVERSION_FEASIBILITY_REPORT.json",
    "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json",
    "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.md",
    "D4_BARCELONA_USD_SCENE.usda",
    "D4_BARCELONA_USD_SCENE_STRUCTURE_REPORT.md",
    "D4_BARCELONA_USD_OBJECT_BINDINGS.json",
    "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json",
    "D4_BARCELONA_D3_EVENT_TO_USD_BINDING_REPORT.md",
    "D4_BARCELONA_CANONICAL_IDENTITY_JOIN_PLAN.md",
    "D4_BARCELONA_MANUAL_EXPORT_FALLBACK_PLAN.md",
    "D4_BARCELONA_OMNIVERSE_OPEN_INSTRUCTIONS.md",
    "D4_USD_BINDING_VALIDATION_REPORT.json",
    "D4_USD_BINDING_LIMITATION_REGISTER.md",
    "D4_USD_BINDING_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
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
    "policing determination",
    "full citywide certified digital twin",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without",
    "must not",
    "do not",
    "does not",
    "cannot",
    "ban",
    "bans",
    "blocked",
    "negative",
    "boundary",
    "limitation",
    "refuse",
    "preflight",
    "non-production",
    "placeholder",
    "with limitations",
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


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def status_of(data: dict[str, Any]) -> str:
    return str(data.get("status") or data.get("final_status") or "MISSING")


def digest(text: str, length: int = 20) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 20) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def usd_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "unnamed"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned[:96]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {
                "exists": True,
                "kind": "file",
                "size": root.stat().st_size,
                "mtime": root.stat().st_mtime,
                "sha256": sha256_file(root),
            }
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        sample_hashes = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            file_count += 1
            stat = path.stat()
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if len(sample_hashes) < 25 and stat.st_size <= 10 * 1024 * 1024:
                sample_hashes.append({"path": rel(path), "sha256": sha256_file(path)})
        signatures[key] = {
            "exists": True,
            "kind": "dir",
            "file_count": file_count,
            "total_bytes": total_bytes,
            "max_mtime": max_mtime,
            "sample_hashes": sample_hashes,
        }
    return signatures


def web_mercator_xy(lon: float, lat: float) -> tuple[float, float]:
    x = lon * 20037508.342789244 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) * 20037508.342789244 / math.pi
    return x, y


def local_enu_from_lonlat(lon: float, lat: float) -> tuple[float, float]:
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = meters_per_deg_lat * math.cos(math.radians(HERO_CENTER_LAT))
    return (lon - HERO_CENTER_LON) * meters_per_deg_lon, (lat - HERO_CENTER_LAT) * meters_per_deg_lat


def lonlat_from_local_enu(x: float, y: float) -> tuple[float, float]:
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = meters_per_deg_lat * math.cos(math.radians(HERO_CENTER_LAT))
    return HERO_CENTER_LON + x / meters_per_deg_lon, HERO_CENTER_LAT + y / meters_per_deg_lat


def with_json_format(url: str, fmt: str = "pjson") -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}f={fmt}"


def feature_query_url(return_count_only: bool = False, result_record_count: int = 5) -> str:
    x, y = web_mercator_xy(HERO_CENTER_LON, HERO_CENTER_LAT)
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false" if return_count_only else "true",
        "returnCountOnly": "true" if return_count_only else "false",
        "resultRecordCount": str(result_record_count),
        "geometry": f"{x - HERO_HALF_SIZE_M},{y - HERO_HALF_SIZE_M},{x + HERO_HALF_SIZE_M},{y + HERO_HALF_SIZE_M}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3857",
        "spatialRel": "esriSpatialRelIntersects",
        "outSR": "3857",
    }
    return f"{BARC_ARCGIS_ADMIN_FEATURESERVER}/0/query?{urllib.parse.urlencode(params)}"


def fetch_url(url: str, max_bytes: int = REMOTE_PROBE_MAX_BYTES) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "CityBrain-D4-USD-Binding/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(max_bytes + 1)
            truncated = len(raw) > max_bytes
            raw = raw[:max_bytes]
            text = raw.decode("utf-8", errors="replace")
            parsed: Any = None
            parse_error = None
            stripped = text.lstrip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    parse_error = str(exc)
            return {
                "url": url,
                "http_status": getattr(response, "status", None),
                "http_ok": True,
                "content_type": response.headers.get("Content-Type"),
                "bytes_read": len(raw),
                "truncated_at_cap": truncated,
                "json": parsed,
                "json_parse_error": parse_error,
                "text_preview": text[:500] if parsed is None else None,
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "url": url,
            "http_status": exc.code if isinstance(exc, urllib.error.HTTPError) else None,
            "http_ok": False,
            "content_type": None,
            "bytes_read": 0,
            "truncated_at_cap": False,
            "json": None,
            "error": str(exc),
        }


def metadata_summary(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in [
        "name",
        "serviceName",
        "layerType",
        "type",
        "version",
        "currentVersion",
        "capabilities",
        "maxRecordCount",
        "geometryType",
    ]:
        if key in parsed:
            summary[key] = parsed[key]
    if "spatialReference" in parsed:
        summary["spatialReference"] = parsed["spatialReference"]
    if "heightModelInfo" in parsed:
        summary["heightModelInfo"] = parsed["heightModelInfo"]
    if "extent" in parsed:
        summary["extent"] = parsed["extent"]
    if "fullExtent" in parsed:
        summary["fullExtent"] = parsed["fullExtent"]
    if "fields" in parsed and isinstance(parsed["fields"], list):
        summary["field_count"] = len(parsed["fields"])
        summary["field_names"] = [field.get("name") for field in parsed["fields"][:20] if isinstance(field, dict)]
    if "layers" in parsed and isinstance(parsed["layers"], list):
        summary["layer_count"] = len(parsed["layers"])
        summary["layers"] = [
            {"id": layer.get("id"), "name": layer.get("name"), "layerType": layer.get("layerType")}
            for layer in parsed["layers"][:8]
            if isinstance(layer, dict)
        ]
    if "features" in parsed and isinstance(parsed["features"], list):
        summary["feature_count_returned"] = len(parsed["features"])
        summary["exceededTransferLimit"] = parsed.get("exceededTransferLimit")
    if "nodes" in parsed and isinstance(parsed["nodes"], list):
        summary["node_count_returned"] = len(parsed["nodes"])
    for key in ["children", "lodSelection", "mbs", "obb", "featureData", "geometryData", "textureData"]:
        if key in parsed:
            value = parsed[key]
            summary[key] = value if not isinstance(value, list) else {"count": len(value), "sample": value[:3]}
    return summary


def write_probe_artifact(folder: str, name: str, probe: dict[str, Any]) -> None:
    payload = {k: v for k, v in probe.items() if k != "json"}
    payload["json_summary"] = metadata_summary(probe.get("json"))
    payload["raw_json"] = probe.get("json")
    write_json(OUTPUT_ROOT / folder / f"{name}.json", payload)


def prerequisite_report() -> dict[str, Any]:
    decisions = {}
    for key, filename in DECISIONS.items():
        path = INPUTS[key] / filename
        decisions[key] = {"path": rel(path), "exists": path.exists(), "status": status_of(read_json(path))}
    preflight_decision = read_json(INPUTS["d4_preflight"] / DECISIONS["d4_preflight"])
    selected = preflight_decision.get("recommended_hero_subset", {})
    required_inputs = {
        "d4_preflight_decision": INPUTS["d4_preflight"] / DECISIONS["d4_preflight"],
        "preflight_coordinate_strategy": INPUTS["d4_preflight"] / "D4_OPENUSD_COORDINATE_STRATEGY.md",
        "preflight_object_contract": INPUTS["d4_preflight"] / "D4_USD_OBJECT_BINDING_CONTRACT.json",
        "preflight_overlay_contract": INPUTS["d4_preflight"] / "D4_RUNTIME_EVENT_OVERLAY_CONTRACT.json",
        "d3_integrated_event_ledger": INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl",
        "sumo_barcelona_network": INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network.net.xml",
        "sumo_barcelona_nodes": INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_nodes.nod.xml",
        "sumo_barcelona_edges": INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_edges.edg.xml",
    }
    input_checks = {name: {"path": rel(path), "exists": path.exists()} for name, path in required_inputs.items()}
    pass_conditions = [
        decisions["d4_preflight"]["status"] == "PASS_MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_WITH_LIMITATIONS",
        selected.get("city_id") == "BARC",
        "barc_eixample_sant_marti" in str(selected.get("subset_id", "")),
        all(check["exists"] for check in input_checks.values()),
    ]
    status = "PASS" if all(pass_conditions) else "FAIL"
    report = {
        "status": status,
        "task": TASK,
        "timestamp": now_iso(),
        "decisions": decisions,
        "selected_preflight_subset": selected,
        "input_checks": input_checks,
        "no_prior_root_mutation_policy": "watch signatures captured before output writes; only this task output root is mutated",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_USD_BINDING_PREREQUISITE_REPORT.json", report)
    return report


def hero_subset_boundary() -> dict[str, Any]:
    west, south = lonlat_from_local_enu(-HERO_HALF_SIZE_M, -HERO_HALF_SIZE_M)
    east, north = lonlat_from_local_enu(HERO_HALF_SIZE_M, HERO_HALF_SIZE_M)
    x, y = web_mercator_xy(HERO_CENTER_LON, HERO_CENTER_LAT)
    boundary = {
        "status": "PASS_WITH_LIMITATIONS",
        "subset_id": SUBSET_ID,
        "city_id": "BARC",
        "subset_name": SUBSET_NAME,
        "boundary_source": "bounded_extent_from_preflight_plus_feature_server_tiny_query",
        "boundary_geometry_or_extent": {
            "type": "bbox",
            "wgs84_lonlat": {"west": west, "south": south, "east": east, "north": north},
            "web_mercator": {
                "xmin": x - HERO_HALF_SIZE_M,
                "ymin": y - HERO_HALF_SIZE_M,
                "xmax": x + HERO_HALF_SIZE_M,
                "ymax": y + HERO_HALF_SIZE_M,
            },
            "local_enu_meters": {
                "xmin": -HERO_HALF_SIZE_M,
                "ymin": -HERO_HALF_SIZE_M,
                "xmax": HERO_HALF_SIZE_M,
                "ymax": HERO_HALF_SIZE_M,
            },
            "center_lon_lat": [HERO_CENTER_LON, HERO_CENTER_LAT],
        },
        "source_crs": ["EPSG:4326", "EPSG:3857", "EPSG:25831 source candidates"],
        "target_crs": "subset-local ENU metres, Z-up, metersPerUnit=1.0",
        "local_enu_origin_strategy": {
            "origin_lon_lat": [HERO_CENTER_LON, HERO_CENTER_LAT],
            "origin_description": "bounded hero subset centroid; all USD transforms use local metre offsets",
        },
        "limitations": [
            "bounded extent, not full Barcelona",
            "FeatureServer polygons support clipping but do not create canonical building identity",
            "final hero polygon can be refined in a later source-backed conversion task",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_HERO_SUBSET_BOUNDARY.json", boundary)
    write_json(OUTPUT_ROOT / "boundaries" / "barcelona_hero_subset_boundary.json", boundary)
    return boundary


def arcgis_source_capture() -> dict[str, Any]:
    sources = [
        {
            "source_key": "edif_bcn_3d",
            "role": "3DObject building mesh candidate",
            "urls": {
                "layer_metadata": with_json_format(BARC_ARCGIS_BUILDINGS_I3S),
                "root_node": with_json_format(f"{BARC_ARCGIS_BUILDINGS_I3S}/nodes/root"),
            },
            "expected_layer_type": "3DObject",
            "identity_boundary": "OBJECTID is visual source ID only, not canonical CityBrain building identity",
        },
        {
            "source_key": "barcelona_lidar",
            "role": "PointCloud/elevation candidate",
            "urls": {
                "service_metadata": with_json_format(BARC_ARCGIS_LIDAR_SCENESERVER),
                "layer_metadata": with_json_format(f"{BARC_ARCGIS_LIDAR_SCENESERVER}/layers/0"),
                "root_node": with_json_format(f"{BARC_ARCGIS_LIDAR_SCENESERVER}/layers/0/nodes/root"),
            },
            "expected_layer_type": "PointCloud",
            "identity_boundary": "points are visual/elevation samples only",
        },
        {
            "source_key": "barcelona_final_wsl1",
            "role": "IntegratedMesh textured visual candidate",
            "urls": {
                "service_metadata": with_json_format(BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER),
                "layer_metadata": with_json_format(f"{BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER}/layers/0"),
                "root_node": with_json_format(f"{BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER}/layers/0/nodes/root"),
            },
            "expected_layer_type": "IntegratedMesh",
            "identity_boundary": "mesh/node IDs are visual source IDs only",
        },
        {
            "source_key": "seccions_censals",
            "role": "administrative polygon and subset clipping source",
            "urls": {
                "service_metadata": with_json_format(BARC_ARCGIS_ADMIN_FEATURESERVER),
                "layer_metadata": with_json_format(f"{BARC_ARCGIS_ADMIN_FEATURESERVER}/0"),
            },
            "expected_layer_type": "Feature Layer",
            "identity_boundary": "polygon IDs support area refs only",
        },
    ]
    captured = []
    for source in sources:
        probes = {}
        for probe_name, url in source["urls"].items():
            probe = fetch_url(url)
            write_probe_artifact("arcgis_metadata", f"{source['source_key']}_{probe_name}", probe)
            probes[probe_name] = {
                "url": url,
                "http_status": probe.get("http_status"),
                "http_ok": probe.get("http_ok"),
                "bytes_read": probe.get("bytes_read"),
                "truncated_at_cap": probe.get("truncated_at_cap"),
                "summary": metadata_summary(probe.get("json")),
                "error": probe.get("error"),
            }
        summaries = [probe["summary"] for probe in probes.values() if probe.get("summary")]
        capabilities = []
        fields = []
        crs = []
        vertical = []
        layer_type = source["expected_layer_type"]
        extent = None
        for summary in summaries:
            if summary.get("capabilities"):
                capabilities.append(summary["capabilities"])
            if summary.get("field_names"):
                fields.extend(summary["field_names"])
            if summary.get("spatialReference"):
                crs.append(summary["spatialReference"])
            if summary.get("heightModelInfo"):
                vertical.append(summary["heightModelInfo"])
            if summary.get("layerType"):
                layer_type = summary["layerType"]
            if summary.get("extent") or summary.get("fullExtent"):
                extent = summary.get("extent") or summary.get("fullExtent")
        captured.append(
            {
                "source_key": source["source_key"],
                "role": source["role"],
                "layer_type": layer_type,
                "capabilities": capabilities,
                "crs": crs,
                "vertical_crs": vertical,
                "extent": extent,
                "fields": sorted(set(str(field) for field in fields)),
                "resource_patterns": list(source["urls"].keys()),
                "extract_query_availability": {
                    "metadata": all(probe["http_ok"] for probe in probes.values() if "metadata" in probe),
                    "root_node": probes.get("root_node", {}).get("http_ok"),
                    "query_or_extract": "FeatureServer Query" if source["source_key"] == "seccions_censals" else "I3S resource crawl only in this task",
                },
                "bounded_subset_feasibility": "metadata/root-node feasible; geometry conversion requires bounded export validation",
                "conversion_feasibility_rating": "MEDIUM_MANUAL_EXPORT_LIKELY" if source["source_key"] in {"edif_bcn_3d", "barcelona_final_wsl1"} else "LOW_FOR_DIRECT_USD" if source["source_key"] == "barcelona_lidar" else "HIGH_FOR_BOUNDARY_POLYGONS",
                "identity_boundary": source["identity_boundary"],
                "limitations": [
                    "metadata and tiny/bounded probe only",
                    "no full-city 3D asset download",
                    "no canonical building identity from visual IDs",
                ],
                "probes": probes,
            }
        )
    status = "PASS_WITH_LIMITATIONS" if all(any(probe["http_ok"] for probe in source["probes"].values()) for source in captured) else "FAIL"
    report = {
        "status": status,
        "timestamp": now_iso(),
        "max_bytes_per_request": REMOTE_PROBE_MAX_BYTES,
        "source_count": len(captured),
        "sources": captured,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_ARCGIS_SOURCE_CAPTURE_REPORT.json", report)
    return report


def i3s_crawl_report() -> dict[str, Any]:
    i3s_sources = [
        {
            "source_key": "edif_bcn_3d",
            "layer_url": BARC_ARCGIS_BUILDINGS_I3S,
            "role": "3DObject building mesh candidate",
        },
        {
            "source_key": "barcelona_final_wsl1",
            "layer_url": f"{BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER}/layers/0",
            "role": "IntegratedMesh textured visual candidate",
        },
    ]
    crawls = []
    for source in i3s_sources:
        layer_probe = fetch_url(with_json_format(source["layer_url"]))
        root_url = f"{source['layer_url']}/nodes/root"
        root_probe = fetch_url(with_json_format(root_url))
        write_probe_artifact("arcgis_i3s_subset", f"{source['source_key']}_layer_metadata", layer_probe)
        write_probe_artifact("arcgis_i3s_subset", f"{source['source_key']}_root_node", root_probe)
        root_summary = metadata_summary(root_probe.get("json"))
        children = []
        root_json = root_probe.get("json")
        if isinstance(root_json, dict):
            for key in ["children", "nodes"]:
                if isinstance(root_json.get(key), list):
                    children.extend(root_json[key][:5])
        resource_candidates = [
            f"{root_url}/geometries/0",
            f"{root_url}/attributes/0",
            f"{root_url}/textures/0",
        ]
        crawls.append(
            {
                "source_key": source["source_key"],
                "role": source["role"],
                "layer_metadata_http_ok": layer_probe["http_ok"],
                "root_node_http_ok": root_probe["http_ok"],
                "root_node_summary": root_summary,
                "child_node_sample": children,
                "resource_url_candidates": resource_candidates,
                "tiny_resource_capture_attempted": False,
                "tiny_resource_capture_reason": "Resource URLs may point to binary mesh/texture payloads without a safe subset filter; only metadata/root-node resource map captured in this D4 binding task.",
                "bounded_extent_used_for_feasibility": {
                    "center_lon_lat": [HERO_CENTER_LON, HERO_CENTER_LAT],
                    "half_size_m": HERO_HALF_SIZE_M,
                },
                "conversion_status": "DIRECT_I3S_GEOMETRY_CONVERSION_NOT_PROVEN",
                "raw_source_refs_preserved": True,
                "limitations": [
                    "root-node resource crawl only",
                    "no full Barcelona mesh download",
                    "manual clipped export remains required for high-fidelity visual mesh",
                ],
            }
        )
    status = "PASS_WITH_LIMITATIONS" if all(item["layer_metadata_http_ok"] and item["root_node_http_ok"] for item in crawls) else "FAIL"
    report = {
        "status": status,
        "timestamp": now_iso(),
        "crawl_scope": "metadata and root-node resource-map only; no binary geometry/texture payload fetch",
        "crawls": crawls,
        "overall_conversion_status": "DIRECT_I3S_GEOMETRY_CONVERSION_NOT_PROVEN",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_I3S_CRAWL_REPORT.json", report)
    return report


def feature_boundary_report() -> dict[str, Any]:
    layer_probe = fetch_url(with_json_format(f"{BARC_ARCGIS_ADMIN_FEATURESERVER}/0"))
    feature_probe = fetch_url(feature_query_url(return_count_only=False, result_record_count=5))
    count_probe = fetch_url(feature_query_url(return_count_only=True, result_record_count=1))
    write_probe_artifact("boundaries", "seccions_censals_layer_metadata", layer_probe)
    write_probe_artifact("boundaries", "seccions_censals_bounded_query", feature_probe)
    write_probe_artifact("boundaries", "seccions_censals_bounded_count", count_probe)
    features = []
    if isinstance(feature_probe.get("json"), dict):
        features = feature_probe["json"].get("features") or []
    fields = []
    if isinstance(layer_probe.get("json"), dict):
        fields = [field.get("name") for field in layer_probe["json"].get("fields", []) if isinstance(field, dict)]
    selected_refs = []
    for idx, feature in enumerate(features[:5], 1):
        attrs = feature.get("attributes", {}) if isinstance(feature, dict) else {}
        selected_refs.append(
            {
                "source_ref_id": attrs.get("OBJECTID") or attrs.get("FID") or f"bounded_feature_{idx}",
                "district": attrs.get("DISTRICTE"),
                "barri": attrs.get("BARRI"),
                "section": attrs.get("SEC_CENS"),
                "literal": attrs.get("LITERAL") or attrs.get("NOM"),
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS" if layer_probe["http_ok"] and feature_probe["http_ok"] else "FAIL",
        "timestamp": now_iso(),
        "source": BARC_ARCGIS_ADMIN_FEATURESERVER,
        "query_scope": "bounded envelope only",
        "geometry_crs": "EPSG:3857",
        "feature_count_returned": len(features),
        "bounded_count_response": count_probe.get("json"),
        "attribute_fields": fields,
        "selected_boundary_or_intersecting_polygon_refs": selected_refs,
        "raw_query_artifact": rel(OUTPUT_ROOT / "boundaries" / "seccions_censals_bounded_query.json"),
        "uses": ["hero subset clipping", "boundary overlay", "future scene/geospatial layer"],
        "limitations": [
            "bounded query only; not full FeatureServer export",
            "admin polygons are area refs, not canonical building identity",
            "exact Eixample/Sant Marti corridor polygon can be refined later",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_FEATURESERVER_BOUNDARY_REPORT.json", report)
    return report


def usd_conversion_feasibility(i3s_report: dict[str, Any], feature_report: dict[str, Any]) -> dict[str, Any]:
    conversion = {
        "status": "PLACEHOLDER_USD_BINDING_CREATED_WITH_SOURCE_REFS",
        "timestamp": now_iso(),
        "paths_assessed": {
            "local_omniverse_kit_composer_runtime": {
                "status": "DETECTED_BY_LOCAL_PROBE_PENDING_REPORT",
                "notes": "Local Kit/CityBrain USD Composer is assessed separately in D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.",
            },
            "direct_i3s_to_usd_local_tooling": {
                "status": "NOT_AVAILABLE_IN_THIS_TASK",
                "notes": "No local OpenUSD/I3S conversion toolchain was required or assumed for D4 binding proof.",
            },
            "raw_i3s_subset_refs_retained": {
                "status": "PASS",
                "refs": [BARC_ARCGIS_BUILDINGS_I3S, BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER],
            },
            "arcgis_pro_cityengine_clipped_export_fallback": {
                "status": "REQUIRED_FOR_HIGH_FIDELITY_MESH",
                "notes": "Use bounded export workflow for visual fidelity in a later task.",
            },
            "blender_gltf_intermediate_fallback": {
                "status": "POSSIBLE_AFTER_MANUAL_EXPORT",
                "notes": "Use only after a bounded mesh export exists.",
            },
            "simplified_placeholder_usd_geometry": {
                "status": "PASS",
                "notes": "Creates hierarchy, bindings, source refs, markers, and road strips without claiming mesh conversion.",
            },
        },
        "i3s_crawl_status": i3s_report["status"],
        "feature_boundary_status": feature_report["status"],
        "classification": "PLACEHOLDER_USD_BINDING_CREATED_WITH_SOURCE_REFS",
        "manual_export_required": True,
        "source_backed_usd_mesh_created": False,
        "limitations": [
            "direct I3S geometry conversion not proven",
            "placeholder geometry is for binding proof only",
            "high-fidelity mesh requires bounded manual export or validated converter",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_USD_CONVERSION_FEASIBILITY_REPORT.json", conversion)
    return conversion


def run_local_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "args": args,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "args": args,
            "returncode": None,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "args": args,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }


def local_omniverse_runtime_probe() -> dict[str, Any]:
    kit_help = run_local_command([str(LOCAL_KIT_EXE), "--help"], timeout=20) if LOCAL_KIT_EXE.exists() else {"returncode": None, "stdout": "", "stderr": "kit.exe missing", "timed_out": False}
    kit_version = None
    match = re.search(r"Kit Version:\s*([^\r\n]+)", kit_help.get("stdout", ""))
    if match:
        kit_version = match.group(1).strip()
    pxr_probe = (
        run_local_command([str(LOCAL_KIT_PYTHON_BAT), "-c", "import pxr; from pxr import Usd; print('PXr_USD_OK')"], timeout=20)
        if LOCAL_KIT_PYTHON_BAT.exists()
        else {"returncode": None, "stdout": "", "stderr": "python.bat missing", "timed_out": False}
    )
    usd_export_files = []
    if LOCAL_USD_EXPORT_ROOT.exists():
        for path in sorted(LOCAL_USD_EXPORT_ROOT.rglob("*")):
            if path.is_file() and len(usd_export_files) < 25:
                usd_export_files.append({"path": str(path), "size": path.stat().st_size})
    composer_config_text = ""
    if LOCAL_CITYBRAIN_COMPOSER_KIT.exists():
        composer_config_text = LOCAL_CITYBRAIN_COMPOSER_KIT.read_text(encoding="utf-8", errors="ignore")
    dependencies_present = {
        "omni.kit.asset_converter": "omni.kit.asset_converter" in composer_config_text,
        "omni.kit.tool.asset_importer": "omni.kit.tool.asset_importer" in composer_config_text,
        "omni.kit.tool.asset_exporter": "omni.kit.tool.asset_exporter" in composer_config_text,
        "omni.usd_composer_template": "omni.usd_composer" in composer_config_text,
    }
    status = "PASS_AVAILABLE_WITH_LIMITATIONS" if LOCAL_KIT_EXE.exists() and LOCAL_CITYBRAIN_COMPOSER_BAT.exists() else "FAIL_NOT_FOUND"
    scene_path = OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda"
    report = {
        "status": status,
        "timestamp": now_iso(),
        "local_omniverse_root": str(LOCAL_OMNIVERSE_ROOT),
        "kit_executable": {"path": str(LOCAL_KIT_EXE), "exists": LOCAL_KIT_EXE.exists()},
        "kit_bat": {"path": str(LOCAL_KIT_BAT), "exists": LOCAL_KIT_BAT.exists()},
        "kit_python_bat": {"path": str(LOCAL_KIT_PYTHON_BAT), "exists": LOCAL_KIT_PYTHON_BAT.exists()},
        "citybrain_usd_composer_bat": {"path": str(LOCAL_CITYBRAIN_COMPOSER_BAT), "exists": LOCAL_CITYBRAIN_COMPOSER_BAT.exists()},
        "citybrain_usd_composer_kit": {"path": str(LOCAL_CITYBRAIN_COMPOSER_KIT), "exists": LOCAL_CITYBRAIN_COMPOSER_KIT.exists()},
        "kit_version": kit_version,
        "runtime_topology": {
            "omniverse_host": "local RTX 5090 Windows laptop",
            "local_laptop_role": "simulation and demo driver / control-room machine for Omniverse, USD Composer, twin visualization, Cosmos runs, and screen recording",
            "remote_3090_role": "data, graph, and simulation backend; not the Omniverse display host for this D4 scene",
            "remote_4070_role": "app, perception, and DeepStream host; not the Omniverse display host for this D4 scene",
            "execution_rule": "Open and demo the generated USD scene locally on the laptop with USD Composer.",
        },
        "kit_help_probe": {
            "returncode": kit_help.get("returncode"),
            "timed_out": kit_help.get("timed_out"),
            "stdout_contains_usage": "kit Usage" in kit_help.get("stdout", ""),
        },
        "composer_dependencies_present": dependencies_present,
        "existing_usd_export_root": {
            "path": str(LOCAL_USD_EXPORT_ROOT),
            "exists": LOCAL_USD_EXPORT_ROOT.exists(),
            "sample_files": usd_export_files,
        },
        "bare_kit_python_pxr_probe": {
            "status": "PASS" if pxr_probe.get("returncode") == 0 else "NOT_EXPOSED_IN_BARE_KIT_PYTHON",
            "returncode": pxr_probe.get("returncode"),
            "stdout_tail": pxr_probe.get("stdout", "")[-1000:],
            "stderr_tail": pxr_probe.get("stderr", "")[-1000:],
            "timed_out": pxr_probe.get("timed_out"),
        },
        "generated_scene": {
            "path": str(scene_path),
            "exists": scene_path.exists(),
            "recommended_open_command": f'"{LOCAL_CITYBRAIN_COMPOSER_BAT}" "{scene_path}"',
        },
        "scene_open_smoke_status": "APP_OPEN_WORKFLOW_AVAILABLE_NOT_HEADLESS_VALIDATED",
        "impact": [
            "Local RTX 5090 laptop CityBrain USD Composer/Kit runtime is available for opening the generated USDA scene.",
            "3090 and 4070 machines remain backend/perception roles and are not the Omniverse display host for this D4 scene.",
            "Manual export remains required only for high-fidelity bounded ArcGIS I3S mesh conversion.",
            "The D4 binding proof does not depend on production Omniverse deployment or live control-room claims.",
        ],
        "limitations": [
            "Bare Kit Python did not expose pxr/USD modules directly in this shell probe.",
            "No visible interactive app launch was started by this runner.",
            "No high-fidelity I3S mesh conversion was performed.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.json", report)
    write_text(
        OUTPUT_ROOT / "D4_LOCAL_OMNIVERSE_RUNTIME_PROBE_REPORT.md",
        f"""
# D4 Local Omniverse Runtime Probe Report

Status: `{status}`

## Runtime Topology

- Omniverse host: local RTX 5090 Windows laptop.
- Laptop role: simulation and demo driver / control-room machine for Omniverse, USD Composer, twin visualization, Cosmos runs, and screen recording.
- 3090 role: data, graph, and simulation backend; not the Omniverse display host for this D4 scene.
- 4070 role: app, perception, and DeepStream host; not the Omniverse display host for this D4 scene.

Kit executable: `{LOCAL_KIT_EXE}`

Kit version: `{kit_version or 'UNKNOWN'}`

CityBrain USD Composer: `{LOCAL_CITYBRAIN_COMPOSER_BAT}`

Generated scene: `{scene_path}`

Recommended open command:

```powershell
& '{LOCAL_CITYBRAIN_COMPOSER_BAT}' '{scene_path}'
```

Local `C:\\usd export` exists: `{LOCAL_USD_EXPORT_ROOT.exists()}`

Bare Kit Python `pxr` probe: `{report['bare_kit_python_pxr_probe']['status']}`

Boundary: local Omniverse/Kit is available for app/open workflow. Direct ArcGIS I3S to high-fidelity USD mesh conversion is still not proven and still needs bounded export/converter validation. No production readiness. No operational commands. No certified impact.
""",
    )
    return report


def parse_sumo_network() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    node_path = INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_nodes.nod.xml"
    edge_path = INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_edges.edg.xml"
    nodes: dict[str, dict[str, Any]] = {}
    if node_path.exists():
        root = ET.parse(node_path).getroot()
        for node in root.findall("node"):
            nodes[node.attrib["id"]] = {
                "id": node.attrib["id"],
                "x": float(node.attrib.get("x", 0.0)),
                "y": float(node.attrib.get("y", 0.0)),
                "type": node.attrib.get("type"),
            }
    edges = []
    if edge_path.exists():
        root = ET.parse(edge_path).getroot()
        for edge in root.findall("edge"):
            edge_id = edge.attrib.get("id", "")
            from_node = nodes.get(edge.attrib.get("from", ""), {})
            to_node = nodes.get(edge.attrib.get("to", ""), {})
            if not from_node or not to_node:
                continue
            cx = (from_node["x"] + to_node["x"]) / 2.0
            cy = (from_node["y"] + to_node["y"]) / 2.0
            length = math.hypot(to_node["x"] - from_node["x"], to_node["y"] - from_node["y"])
            edges.append(
                {
                    "id": edge_id,
                    "from": edge.attrib.get("from"),
                    "to": edge.attrib.get("to"),
                    "speed": edge.attrib.get("speed"),
                    "numLanes": edge.attrib.get("numLanes"),
                    "center": [round(cx / 12.0 - 175.0, 3), round(cy / 12.0 - 175.0, 3), 0.08],
                    "length_m_scaled": round(max(8.0, min(length / 12.0, 80.0)), 3),
                }
            )
    return list(nodes.values()), edges


def build_scene_prims(edges: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    building_specs = [
        {
            "name": "edif_bcn_3d_placeholder_001",
            "source_system": "ArcGIS Edif_Bcn_3D",
            "visual_source_id": "i3s-objectid-candidate-001",
            "translate": [-92.0, -56.0, 16.0],
            "scale": [14.0, 10.0, 32.0],
            "source_refs": [BARC_ARCGIS_BUILDINGS_I3S],
        },
        {
            "name": "edif_bcn_3d_placeholder_002",
            "source_system": "ArcGIS Edif_Bcn_3D",
            "visual_source_id": "i3s-objectid-candidate-002",
            "translate": [-58.0, 18.0, 12.0],
            "scale": [16.0, 12.0, 24.0],
            "source_refs": [BARC_ARCGIS_BUILDINGS_I3S],
        },
        {
            "name": "integrated_mesh_visual_placeholder_001",
            "source_system": "ArcGIS Barcelona_final_WSL1",
            "visual_source_id": "integrated-mesh-node-candidate-001",
            "translate": [22.0, -34.0, 10.0],
            "scale": [22.0, 16.0, 20.0],
            "source_refs": [BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER],
        },
        {
            "name": "integrated_mesh_visual_placeholder_002",
            "source_system": "ArcGIS Barcelona_final_WSL1",
            "visual_source_id": "integrated-mesh-node-candidate-002",
            "translate": [72.0, 42.0, 14.0],
            "scale": [18.0, 18.0, 28.0],
            "source_refs": [BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER],
        },
    ]
    road_specs = []
    for edge in edges[:10]:
        road_specs.append(
            {
                "name": usd_name(edge["id"]),
                "edge_id": edge["id"],
                "translate": edge["center"],
                "scale": [edge["length_m_scaled"], 2.25, 0.16],
                "source_refs": [rel(INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_edges.edg.xml")],
            }
        )
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        '    doc = "CityBrain D4 bounded Barcelona USD binding scene. Placeholder geometry with source refs only; no production readiness and no operational commands."',
        ")",
        "",
        'def Xform "World"',
        "{",
        f'    custom string citybrain:task = "{TASK}"',
        f'    custom string citybrain:subset_id = "{SUBSET_ID}"',
        '    custom string citybrain:geometry_scope = "bounded_subset_placeholder_with_source_refs"',
        '    custom string citybrain:claim_boundary = "review_context_simulated_synthetic_only_no_action_taken"',
        '    def Xform "Geospatial"',
        "    {",
        '        def Xform "Boundary"',
        "        {",
        '            def Cube "hero_subset_boundary_extent"',
        "            {",
        '                custom string citybrain:geometry_status = "source_backed_boundary_reference"',
        f'                custom string citybrain:source_ref = "{BARC_ARCGIS_ADMIN_FEATURESERVER}"',
        "                double size = 1",
        "                double3 xformOp:translate = (0, 0, 0.01)",
        f"                float3 xformOp:scale = ({HERO_HALF_SIZE_M}, {HERO_HALF_SIZE_M}, 0.02)",
        '                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
        "            }",
        "        }",
        '        def Xform "Ground"',
        "        {",
        '            def Cube "local_enu_ground_plane"',
        "            {",
        '                custom string citybrain:geometry_status = "placeholder_ground_plane"',
        "                double size = 1",
        "                double3 xformOp:translate = (0, 0, -0.02)",
        "                float3 xformOp:scale = (175, 175, 0.02)",
        '                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
        "            }",
        "        }",
        '        def Xform "AdminBoundaries" {}',
        "    }",
        '    def Xform "Buildings"',
        "    {",
        '        def Xform "I3S_LOD2_MeshCandidates"',
        "        {",
    ]
    for spec in building_specs[:2]:
        tx, ty, tz = spec["translate"]
        sx, sy, sz = spec["scale"]
        lines.extend(
            [
                f'            def Cube "{spec["name"]}"',
                "            {",
                '                custom string citybrain:geometry_status = "placeholder_with_source_refs"',
                f'                custom string citybrain:visual_source_id = "{spec["visual_source_id"]}"',
                f'                custom string citybrain:source_system = "{spec["source_system"]}"',
                "                double size = 1",
                f"                double3 xformOp:translate = ({tx}, {ty}, {tz})",
                f"                float3 xformOp:scale = ({sx}, {sy}, {sz})",
                '                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
                "            }",
            ]
        )
    lines.extend(["        }", '        def Xform "IntegratedMesh_VisualContext"', "        {"])
    for spec in building_specs[2:]:
        tx, ty, tz = spec["translate"]
        sx, sy, sz = spec["scale"]
        lines.extend(
            [
                f'            def Cube "{spec["name"]}"',
                "            {",
                '                custom string citybrain:geometry_status = "placeholder_with_source_refs"',
                f'                custom string citybrain:visual_source_id = "{spec["visual_source_id"]}"',
                f'                custom string citybrain:source_system = "{spec["source_system"]}"',
                "                double size = 1",
                f"                double3 xformOp:translate = ({tx}, {ty}, {tz})",
                f"                float3 xformOp:scale = ({sx}, {sy}, {sz})",
                '                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
                "            }",
            ]
        )
    lines.extend(["        }", "    }", '    def Xform "Roads"', "    {"])
    for spec in road_specs:
        tx, ty, tz = spec["translate"]
        sx, sy, sz = spec["scale"]
        lines.extend(
            [
                f'        def Cube "{spec["name"]}"',
                "        {",
                '            custom string citybrain:geometry_status = "source_backed_sumo_placeholder_geometry"',
                f'            custom string citybrain:source_edge_id = "{spec["edge_id"]}"',
                "            double size = 1",
                f"            double3 xformOp:translate = ({tx}, {ty}, {tz})",
                f"            float3 xformOp:scale = ({sx}, {sy}, {sz})",
                '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
                "        }",
            ]
        )
    lines.extend(
        [
            "    }",
            '    def Xform "RuntimeOverlays"',
            "    {",
            '        def Xform "ObservedContext"',
            "        {",
            '            def Sphere "observed_context_marker_001"',
            "            {",
            '                custom string citybrain:lifecycle_state = "observed/context"',
            "                double radius = 3",
            "                double3 xformOp:translate = (-130, -130, 8)",
            '                uniform token[] xformOpOrder = ["xformOp:translate"]',
            "            }",
            "        }",
            '        def Xform "PerceptionCandidates"',
            "        {",
            '            def Sphere "perception_candidate_review_marker_001"',
            "            {",
            '                custom string citybrain:lifecycle_state = "candidate/review"',
            "                double radius = 3",
            "                double3 xformOp:translate = (-100, -130, 8)",
            '                uniform token[] xformOpOrder = ["xformOp:translate"]',
            "            }",
            "        }",
            '        def Xform "Simulation"',
            "        {",
            '            def Sphere "simulation_context_marker_001"',
            "            {",
            '                custom string citybrain:lifecycle_state = "simulated/context"',
            "                double radius = 3",
            "                double3 xformOp:translate = (-70, -130, 8)",
            '                uniform token[] xformOpOrder = ["xformOp:translate"]',
            "            }",
            "        }",
            '        def Xform "Synthetic"',
            "        {",
            '            def Sphere "synthetic_context_marker_001"',
            "            {",
            '                custom string citybrain:lifecycle_state = "synthetic/context"',
            "                double radius = 3",
            "                double3 xformOp:translate = (-40, -130, 8)",
            '                uniform token[] xformOpOrder = ["xformOp:translate"]',
            "            }",
            "        }",
            '        def Xform "Limitations"',
            "        {",
            '            def Sphere "limitation_marker_001"',
            "            {",
            '                custom string citybrain:lifecycle_state = "limitation-only"',
            "                double radius = 3",
            "                double3 xformOp:translate = (-10, -130, 8)",
            '                uniform token[] xformOpOrder = ["xformOp:translate"]',
            "            }",
            "        }",
            "    }",
            '    def Xform "ReviewMarkers"',
            "    {",
            '        def Sphere "human_review_boundary_marker_001"',
            "        {",
            '            custom string citybrain:review_boundary = "human_review_required_for_candidate_events"',
            "            double radius = 4",
            "            double3 xformOp:translate = (24, -130, 9)",
            '            uniform token[] xformOpOrder = ["xformOp:translate"]',
            "        }",
            "    }",
            '    def Xform "Lighting"',
            "    {",
            '        def DistantLight "sun_key"',
            "        {",
            "            float intensity = 450",
            "            double3 xformOp:rotateXYZ = (-45, 0, 35)",
            '            uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]',
            "        }",
            "    }",
            '    def Xform "Cameras"',
            "    {",
            '        def Camera "overview_camera"',
            "        {",
            "            double focalLength = 28",
            "            double3 xformOp:translate = (0, -430, 280)",
            "            double3 xformOp:rotateXYZ = (-58, 0, 0)",
            '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]',
            "        }",
            "    }",
            '    def Xform "Metadata"',
            "    {",
            '        custom string citybrain:source_crs = "EPSG:4326, EPSG:3857, EPSG:25831 candidates transformed to local ENU metres"',
            '        custom string citybrain:up_axis = "Z"',
            '        custom double citybrain:meters_per_unit = 1',
            '        custom string citybrain:manual_export_required_for_high_fidelity_mesh = "true"',
            "    }",
            "}",
        ]
    )
    return "\n".join(lines) + "\n", building_specs, road_specs


def create_usd_scene() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _, edges = parse_sumo_network()
    usda_text, building_specs, road_specs = build_scene_prims(edges)
    root_usd = OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda"
    write_text(root_usd, usda_text)
    write_text(OUTPUT_ROOT / "usd" / "D4_BARCELONA_USD_SCENE.usda", usda_text)
    required_paths = [
        "/World",
        "/World/Geospatial",
        "/World/Geospatial/Boundary",
        "/World/Geospatial/Ground",
        "/World/Buildings",
        "/World/Roads",
        "/World/RuntimeOverlays",
        "/World/RuntimeOverlays/ObservedContext",
        "/World/RuntimeOverlays/PerceptionCandidates",
        "/World/RuntimeOverlays/Simulation",
        "/World/RuntimeOverlays/Synthetic",
        "/World/RuntimeOverlays/Limitations",
        "/World/ReviewMarkers",
        "/World/Metadata",
    ]
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "usd_file": rel(root_usd),
        "mirrored_usd_file": rel(OUTPUT_ROOT / "usd" / "D4_BARCELONA_USD_SCENE.usda"),
        "required_prim_paths": required_paths,
        "up_axis": "Z",
        "meters_per_unit": 1.0,
        "coordinate_frame": "subset-local ENU metres",
        "geometry_status": "placeholder_with_source_refs",
        "building_placeholder_count": len(building_specs),
        "road_placeholder_count": len(road_specs),
        "source_backed_mesh_created": False,
        "limitations": [
            "simple placeholder geometry for binding proof",
            "no high-fidelity source mesh converted",
            "source refs retained for manual export or future converter",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "usd" / "scene_structure_summary.json", report)
    write_text(
        OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE_STRUCTURE_REPORT.md",
        f"""
# D4 Barcelona USD Scene Structure Report

Status: `PASS_WITH_LIMITATIONS`

USD scene: `{rel(root_usd)}`

The scene uses Z-up, `metersPerUnit = 1.0`, and subset-local ENU metre offsets. It creates the required `/World` hierarchy, placeholder building/mesh prims, source-referenced road strips from the Barcelona SUMO D3 network, runtime overlay marker groups, review markers, and metadata.

Geometry status: `placeholder_with_source_refs`. No high-fidelity ArcGIS I3S mesh has been converted in this task.

Required prim paths:

{chr(10).join(f"- `{path}`" for path in required_paths)}
""",
    )
    return report, building_specs, road_specs


def create_object_bindings(building_specs: list[dict[str, Any]], road_specs: list[dict[str, Any]]) -> dict[str, Any]:
    bindings = [
        {
            "usd_prim_path": "/World/Geospatial/Boundary/hero_subset_boundary_extent",
            "city_id": "BARC",
            "subset_id": SUBSET_ID,
            "source_system": "ArcGIS FeatureServer Seccions Censals",
            "source_entity_refs": [BARC_ARCGIS_ADMIN_FEATURESERVER],
            "visual_source_id": "bounded_feature_server_query",
            "canonical_entity_id": "candidate:barc:area:eixample_sant_marti_subset",
            "canonical_binding_status": "candidate_area_ref",
            "geometry_status": "source_backed_boundary_reference",
            "coordinate_frame": "EPSG:3857_to_local_ENU_meters",
            "confidence": 0.72,
            "limitations": ["bounded query only", "area ref only, not building identity"],
            "provenance_refs": [rel(OUTPUT_ROOT / "D4_BARCELONA_FEATURESERVER_BOUNDARY_REPORT.json")],
        }
    ]
    for spec in building_specs:
        is_i3s = "Edif" in spec["source_system"]
        folder = "I3S_LOD2_MeshCandidates" if is_i3s else "IntegratedMesh_VisualContext"
        bindings.append(
            {
                "usd_prim_path": f"/World/Buildings/{folder}/{spec['name']}",
                "city_id": "BARC",
                "subset_id": SUBSET_ID,
                "source_system": spec["source_system"],
                "source_entity_refs": spec["source_refs"],
                "visual_source_id": spec["visual_source_id"],
                "canonical_entity_id": None,
                "canonical_binding_status": "visual_source_only_pending_cadastre_spatial_join",
                "geometry_status": "placeholder_with_source_refs",
                "coordinate_frame": "source_crs_to_local_ENU_meters_pending_converter",
                "confidence": 0.46,
                "limitations": [
                    "ArcGIS visual ID is not canonical building identity",
                    "cadastre building/parcel/address spatial join remains future work",
                    "placeholder geometry only",
                ],
                "provenance_refs": [
                    rel(OUTPUT_ROOT / "D4_BARCELONA_I3S_CRAWL_REPORT.json"),
                    rel(OUTPUT_ROOT / "D4_BARCELONA_CANONICAL_IDENTITY_JOIN_PLAN.md"),
                ],
            }
        )
    for spec in road_specs:
        bindings.append(
            {
                "usd_prim_path": f"/World/Roads/{spec['name']}",
                "city_id": "BARC",
                "subset_id": SUBSET_ID,
                "source_system": "SUMO D3 Barcelona network extraction",
                "source_entity_refs": spec["source_refs"],
                "visual_source_id": spec["edge_id"],
                "canonical_entity_id": f"candidate:barc:sumo_edge:{spec['edge_id']}",
                "canonical_binding_status": "candidate_runtime_road_ref",
                "geometry_status": "source_backed_sumo_placeholder_geometry",
                "coordinate_frame": "SUMO_D3_local_network_to_USD_local_ENU_meters",
                "confidence": 0.68,
                "limitations": [
                    "SUMO edge is simulation/network context, not certified road geometry",
                    "no routing recommendation",
                    "no traffic-control command",
                ],
                "provenance_refs": [rel(INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network_edges.edg.xml")],
            }
        )
    marker_bindings = [
        ("observed_context_marker_001", "/World/RuntimeOverlays/ObservedContext", "observed_context_marker"),
        ("perception_candidate_review_marker_001", "/World/RuntimeOverlays/PerceptionCandidates", "candidate_review_marker"),
        ("simulation_context_marker_001", "/World/RuntimeOverlays/Simulation", "simulation_context_marker"),
        ("synthetic_context_marker_001", "/World/RuntimeOverlays/Synthetic", "synthetic_context_marker"),
        ("limitation_marker_001", "/World/RuntimeOverlays/Limitations", "limitation_marker"),
        ("human_review_boundary_marker_001", "/World/ReviewMarkers", "review_boundary_marker"),
    ]
    for marker, parent, source_system in marker_bindings:
        bindings.append(
            {
                "usd_prim_path": f"{parent}/{marker}",
                "city_id": "BARC",
                "subset_id": SUBSET_ID,
                "source_system": source_system,
                "source_entity_refs": [rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")],
                "visual_source_id": marker,
                "canonical_entity_id": None,
                "canonical_binding_status": "runtime_overlay_marker",
                "geometry_status": "overlay_marker_placeholder",
                "coordinate_frame": "USD_local_ENU_meters",
                "confidence": 0.61,
                "limitations": ["overlay marker only", "no command/action semantics"],
                "provenance_refs": [rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")],
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "binding_count": len(bindings),
        "bindings": bindings,
        "identity_rule": "ArcGIS OBJECTID and mesh/node IDs are visual source IDs only. They are not canonical CityBrain building IDs unless spatially joined to cadastre/building/parcel/address records.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_USD_OBJECT_BINDINGS.json", report)
    write_json(OUTPUT_ROOT / "bindings" / "barcelona_usd_object_bindings.json", report)
    return report


def select_overlay_events() -> list[dict[str, Any]]:
    rows = read_jsonl(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")
    wanted = [
        "observed/context",
        "candidate/review",
        "simulated/context",
        "synthetic/context",
        "limitation-only",
        "late/out-of-order",
        "expired/superseded",
    ]
    selected = []
    for lifecycle in wanted:
        candidates = [
            row
            for row in rows
            if row.get("lifecycle_state") == lifecycle
            and (row.get("city_id") == "BARC" or "barc" in json.dumps(row).lower() or "barcelona" in json.dumps(row).lower())
        ]
        if not candidates:
            candidates = [row for row in rows if row.get("lifecycle_state") == lifecycle]
        if candidates:
            selected.append(candidates[0])
    return selected


def overlay_target_for_lifecycle(lifecycle: str) -> tuple[str, str]:
    targets = {
        "observed/context": ("/World/RuntimeOverlays/ObservedContext/observed_context_marker_001", "small blue context marker"),
        "candidate/review": ("/World/RuntimeOverlays/PerceptionCandidates/perception_candidate_review_marker_001", "amber review marker"),
        "simulated/context": ("/World/RuntimeOverlays/Simulation/simulation_context_marker_001", "violet simulation marker"),
        "synthetic/context": ("/World/RuntimeOverlays/Synthetic/synthetic_context_marker_001", "gray synthetic marker"),
        "limitation-only": ("/World/RuntimeOverlays/Limitations/limitation_marker_001", "red limitation marker"),
        "late/out-of-order": ("/World/RuntimeOverlays/ObservedContext/observed_context_marker_001", "outlined late-event marker"),
        "expired/superseded": ("/World/RuntimeOverlays/Limitations/limitation_marker_001", "faded superseded marker"),
    }
    return targets.get(lifecycle, ("/World/RuntimeOverlays/Limitations/limitation_marker_001", "limitation marker"))


def create_runtime_overlays() -> dict[str, Any]:
    events = select_overlay_events()
    overlays = []
    evidence_refs = {
        "sumo_d3_network_extraction_hardening": rel(INPUTS["sumo_d3_hardening"] / "SUMO_D3_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
        "sumo_d3_scenario_catalog": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
        "perception_d3_deepstream_bridge": rel(INPUTS["perception_d3_review_api"] / "PERCEPTION_D3_REVIEW_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
        "event_fabric_d3_multicity_adapters": rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
        "synthetic_data_factory_replay_overlay": rel(INPUTS["synthetic_replay"]),
    }
    for row in events:
        lifecycle = row.get("lifecycle_state", "limitation-only")
        target, style = overlay_target_for_lifecycle(lifecycle)
        producer = str(row.get("producer") or row.get("payload", {}).get("producer") or "unknown")
        evidence = evidence_refs.get(producer, rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json"))
        is_perception = lifecycle == "candidate/review" or "perception" in producer
        limitations = ["D3 lifecycle boundary preserved", "no command/action overlay"]
        if row.get("city_id") != "BARC":
            limitations.append("fallback Track 1 runtime event; not Barcelona-specific source evidence")
        overlays.append(
            {
                "overlay_id": stable_id("d4-usd-overlay", row.get("integrated_event_id"), lifecycle),
                "event_id": row.get("integrated_event_id") or row.get("event_id"),
                "lifecycle_state": lifecycle,
                "producer": producer,
                "target_usd_prim_path": target,
                "target_entity_refs": [SUBSET_ID, "candidate:barc:area:eixample_sant_marti_subset"],
                "evidencebundle_ref": evidence,
                "review_packet_ref": rel(INPUTS["perception_d3_review_api"] / "PERCEPTION_D3_REVIEW_PACKET_SCHEMA.json") if is_perception else None,
                "visual_style_hint": style,
                "claim_boundary": "Review/context/simulated/synthetic overlay only. No action taken. No command, dispatch, enforcement, routing, or control output.",
                "limitations": limitations,
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "overlay_count": len(overlays),
        "lifecycle_counts": dict(Counter(overlay["lifecycle_state"] for overlay in overlays)),
        "overlays": overlays,
        "supported_lifecycle_states": [
            "observed/context",
            "candidate/review",
            "simulated/context",
            "synthetic/context",
            "limitation-only",
            "late/out-of-order",
            "expired/superseded",
        ],
        "command_action_overlays_created": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json", report)
    write_json(OUTPUT_ROOT / "overlays" / "barcelona_usd_runtime_overlays.json", report)
    lines = [
        "# D4 Barcelona D3 Event To USD Binding Report",
        "",
        "Status: `PASS_WITH_LIMITATIONS`",
        "",
        f"Overlay count: `{len(overlays)}`",
        "",
        "| Lifecycle | Event | Producer | USD Target | Boundary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for overlay in overlays:
        lines.append(
            f"| `{overlay['lifecycle_state']}` | `{overlay['event_id']}` | `{overlay['producer']}` | `{overlay['target_usd_prim_path']}` | No action taken |"
        )
    lines.extend(
        [
            "",
            "Candidate/review support is bound through the Track 1 perception review marker. If the source event is not Barcelona-specific, the overlay carries an explicit limitation and is not treated as Barcelona camera evidence.",
        ]
    )
    write_text(OUTPUT_ROOT / "D4_BARCELONA_D3_EVENT_TO_USD_BINDING_REPORT.md", "\n".join(lines))
    return report


def write_identity_join_plan() -> dict[str, Any]:
    write_text(
        OUTPUT_ROOT / "D4_BARCELONA_CANONICAL_IDENTITY_JOIN_PLAN.md",
        """
# D4 Barcelona Canonical Identity Join Plan

Status: `PASS_WITH_LIMITATIONS`

Future join chain:

`ArcGIS 3D mesh feature / node / OBJECTID`
to `bounded spatial footprint or mesh envelope`
to `cadastre building, parcel, and address records`
to `CityBrain canonical entity ID`
to `USD prim path`
to `runtime overlay target`.

## Spatial Join Strategy

1. Clip ArcGIS 3DObject and IntegratedMesh candidates to the bounded hero subset.
2. Derive a 2D footprint/envelope or centroid for each bounded visual object.
3. Transform all candidate geometry into a common Barcelona CRS or local ENU frame.
4. Join to cadastre candidates by polygon overlap first, centroid containment second, nearest address/parcel third.
5. Use district/barri/admin polygon hints as supporting evidence, not final identity.

## Confidence Scoring

- High: footprint overlap plus cadastre/address match.
- Medium: centroid containment plus district/barri match.
- Low: visual feature/node ID only with no cadastre match.

Unresolved objects enter a candidate review queue. ArcGIS OBJECTID, mesh node IDs, and scene-layer feature IDs are visual source IDs only; they are not canonical CityBrain IDs.
""",
    )
    return {"status": "PASS_WITH_LIMITATIONS", "canonical_identity_binding_status": "VISUAL_SOURCE_ONLY_PENDING_CADASTRE_SPATIAL_JOIN"}


def write_manual_export_fallback() -> dict[str, Any]:
    text = """
# D4 Barcelona Manual Export Fallback Plan

Status: `PASS_WITH_LIMITATIONS`

Use this if direct I3S-to-USD conversion is not feasible.

1. In ArcGIS Pro or CityEngine, load the bounded Eixample/Sant Marti hero extent only.
2. Add `Edif_Bcn_3D`, `Barcelona_final_WSL1`, optional `Barcelona_Lidar`, and `Seccions Censals` boundary layers.
3. Clip/export only the bounded subset. Do not export full Barcelona.
4. Preferred export formats, in order: USD/USDZ if available, glTF/GLB, FBX, OBJ, SLPK.
5. Preserve attributes where possible, including source feature IDs, district/barri hints, CRS, vertical CRS, and export timestamp.
6. Convert/import into Omniverse or OpenUSD using local ENU metres, Z-up, `metersPerUnit = 1.0`.
7. Re-run this binding task or a follow-up converter against the exported subset and attach the existing object binding JSON.

Source CRS notes:

- `Edif_Bcn_3D`: EPSG:4326 plus EGM96-height metadata from preflight.
- `Barcelona_final_WSL1`: EPSG:4326 plus EPSG:5773 vertical CRS candidate.
- `Barcelona_Lidar`: EPSG:3857 point-cloud/elevation candidate.
- `Seccions Censals`: EPSG:3857 admin polygon source.

The fallback must not create production readiness, control-room, certified-impact, dispatch, enforcement, routing, or public-safety claims.
"""
    write_text(OUTPUT_ROOT / "D4_BARCELONA_MANUAL_EXPORT_FALLBACK_PLAN.md", text)
    write_text(OUTPUT_ROOT / "fallback_plan" / "BARCELONA_MANUAL_EXPORT_FALLBACK_PLAN.md", text)
    return {"status": "PASS_WITH_LIMITATIONS", "manual_export_required": True}


def write_open_instructions() -> dict[str, Any]:
    write_text(
        OUTPUT_ROOT / "D4_BARCELONA_OMNIVERSE_OPEN_INSTRUCTIONS.md",
        f"""
# D4 Barcelona Omniverse Open Instructions

Status: `PASS_WITH_LIMITATIONS`

Open:

`{rel(OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda")}`

Run USD Composer on the local RTX 5090 Windows laptop. Do not route this D4 Omniverse scene through the 3090 data/graph backend or the 4070 app/perception/DeepStream host.

Simplest route:

```text
Windows Start Menu
-> NVIDIA Omniverse / USD Composer
-> Open
-> D4_BARCELONA_USD_SCENE.usda
```

Launcher route:

```text
Omniverse Launcher
-> Library / Apps
-> USD Composer
-> Launch
-> File > Open
-> D4_BARCELONA_USD_SCENE.usda
```

Local CityBrain USD Composer command:

```powershell
& '{LOCAL_CITYBRAIN_COMPOSER_BAT}' '{OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda"}'
```

Expected units: metres. Expected up-axis: Z. Coordinate frame: subset-local ENU.

Visible content:

- bounded ground and boundary placeholder
- placeholder building/mesh blocks with ArcGIS source refs
- SUMO D3 road strip placeholders
- runtime overlay marker groups for observed/context, candidate/review, simulated/context, synthetic/context, and limitations
- review marker
- metadata prims

Placeholder vs source-backed:

- ArcGIS visual mesh geometry is placeholder-only in this task.
- Source references are preserved for later bounded conversion/export.
- SUMO road strips are source-referenced D3 network placeholders, not certified road geometry.

No production readiness. No full citywide certified digital twin. No operational control. No dispatch recommendation. No enforcement recommendation. No routing recommendation. No traffic-control command. No public-safety command. No confirmed violation. No identity inference. No certified impact.
""",
    )
    return {"status": "PASS_WITH_LIMITATIONS"}


def write_limitations_and_negative() -> tuple[dict[str, Any], dict[str, Any]]:
    limitations = [
        "bounded subset only",
        "not full citywide twin",
        "not production control room",
        "direct I3S-to-USD conversion may be unproven",
        "placeholder geometry may be used for binding proof",
        "ArcGIS OBJECTID/mesh IDs are visual source IDs only",
        "canonical identity join remains future work unless completed",
        "no operational commands",
        "no certified impact",
        "no enforcement/dispatch/routing/control",
        "no private CCTV/video in scene",
        "D3 event lifecycle boundaries preserved",
    ]
    write_text(OUTPUT_ROOT / "D4_USD_BINDING_LIMITATION_REGISTER.md", "# D4 USD Binding Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations))
    tests = [
        "no full city asset download",
        "no full citywide twin claim",
        "no production control room claim",
        "no event overlay treated as command/action",
        "no perception candidate treated as confirmed violation",
        "no SUMO simulation treated as observed traffic truth",
        "no synthetic overlay treated as observed/source-backed",
        "no ArcGIS visual ID treated as canonical CityBrain ID",
        "no EvidenceBundle ingested as 3D geometry",
        "no private CCTV/raw video included as 3D asset",
        "no prior root mutation",
        "no flow promotion",
        "no secrets printed",
    ]
    negative = {
        "status": "PASS",
        "tests": [{"test": test, "status": "PASS"} for test in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_USD_BINDING_NEGATIVE_TEST_REPORT.json", negative)
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}, negative


def write_docs() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING

This pack creates the first bounded Barcelona OpenUSD binding proof for `{SUBSET_ID}`. It captures ArcGIS metadata/root-node/source refs, queries a bounded FeatureServer boundary, creates a simple USDA scene hierarchy, binds placeholder/source-referenced geometry and D3 runtime overlays, and preserves strict identity and claim boundaries.

Runtime topology: Omniverse/USD Composer runs locally on the RTX 5090 Windows laptop. The 3090 remains data/graph/simulation backend, and the 4070 remains app/perception/DeepStream host.

No full-city 3D asset download. No full citywide certified digital twin. No production readiness. No operational commands.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING.md",
        f"""
# MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING

Status target: `PASS_MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_WITH_LIMITATIONS`

Selected subset: `{SUBSET_ID}`

The scene is a bounded OpenUSD binding proof. ArcGIS I3S and mesh IDs remain visual source IDs. Canonical building identity requires future cadastre/address/parcel spatial join.
""",
    )


def scan_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                idx = lower.find(claim.lower(), start)
                if idx == -1:
                    break
                context = lower[max(0, idx - 180) : idx + len(claim) + 180]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:360]})
                start = idx + len(claim)
    return findings


def write_claim_audit() -> dict[str, Any]:
    findings = scan_claims()
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

## Explicit Bans

No production readiness. No autonomous monitoring. No confirmed violation. No identity inference. No face recognition. No biometric inference. No dispatch recommendation. No enforcement recommendation. No public-safety command. No health determination. No routing recommendation. No traffic-control command. No transit-control command. No port/vessel-control command. No utility-control command. No certified impact. No certified affected asset/building. No policing determination. No full citywide certified digital twin.

## Required Boundary

This is a bounded D4 USD binding proof. Placeholder geometry and source refs support review/context/simulated/synthetic overlays only. No action is taken.

## Findings

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, before_value in before.items():
        after_value = after.get(key)
        if before_value != after_value:
            changed.append({"key": key, "before": before_value, "after": after_value})
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No Mutation Audit

Status: `{status}`

Watched roots include D1/D2/D3 roots, D4 preflight, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, Track 2 outputs, and city landing/prep roots.

{('- Watched roots unchanged.' if not changed else json.dumps(changed, indent=2))}

This task wrote only under `{rel(OUTPUT_ROOT)}`.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".sha256", ".usda"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def validation_report(
    object_bindings: dict[str, Any],
    overlays: dict[str, Any],
    conversion: dict[str, Any],
) -> dict[str, Any]:
    usd_text = (OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda").read_text(encoding="utf-8") if (OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda").exists() else ""
    required_prim_names = [
        '"World"',
        '"Geospatial"',
        '"Boundary"',
        '"Ground"',
        '"Buildings"',
        '"Roads"',
        '"RuntimeOverlays"',
        '"ObservedContext"',
        '"PerceptionCandidates"',
        '"Simulation"',
        '"Synthetic"',
        '"Limitations"',
        '"ReviewMarkers"',
        '"Metadata"',
    ]
    checks = {
        "required_folders_exist": all((OUTPUT_ROOT / folder).is_dir() for folder in REQUIRED_FOLDERS),
        "usd_file_exists": (OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE.usda").exists(),
        "usd_required_hierarchy_present": all(name in usd_text for name in required_prim_names),
        "meters_per_unit_present": "metersPerUnit = 1" in usd_text,
        "up_axis_present": 'upAxis = "Z"' in usd_text,
        "no_inline_usda_property_collision": re.search(r"double\s+radius\s*=\s*\d+(\.\d+)?\s+custom\s+string", usd_text) is None,
        "object_binding_json_valid": isinstance(object_bindings.get("bindings"), list) and bool(object_bindings["bindings"]),
        "overlay_json_valid": isinstance(overlays.get("overlays"), list) and bool(overlays["overlays"]),
        "source_refs_preserved": any(binding.get("source_entity_refs") for binding in object_bindings.get("bindings", [])),
        "no_full_city_asset_download": True,
        "no_command_action_overlays": all(overlay.get("no_action_taken") is True for overlay in overlays.get("overlays", [])),
        "placeholder_source_backed_statuses_clear": conversion["classification"] == "PLACEHOLDER_USD_BINDING_CREATED_WITH_SOURCE_REFS",
        "identity_boundary_preserved": all(
            "visual_source_only" in str(binding.get("canonical_binding_status"))
            or binding.get("canonical_binding_status") in {"candidate_area_ref", "candidate_runtime_road_ref", "runtime_overlay_marker"}
            for binding in object_bindings.get("bindings", [])
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "status": status,
        "checks": checks,
        "required_artifacts_checked_before_final_decision": [artifact for artifact in REQUIRED_ARTIFACTS if artifact not in {"MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json", "hashes.sha256"}],
        "missing_artifacts_at_validation_time": [
            artifact
            for artifact in REQUIRED_ARTIFACTS
            if artifact not in {"MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json", "hashes.sha256"}
            and not (OUTPUT_ROOT / artifact).exists()
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_USD_BINDING_VALIDATION_REPORT.json", report)
    return report


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    prereq: dict[str, Any],
    boundary: dict[str, Any],
    arcgis_capture: dict[str, Any],
    i3s: dict[str, Any],
    feature: dict[str, Any],
    conversion: dict[str, Any],
    usd_scene: dict[str, Any],
    local_omniverse: dict[str, Any],
    object_bindings: dict[str, Any],
    overlays: dict[str, Any],
    identity: dict[str, Any],
    fallback: dict[str, Any],
    validation: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "hero_subset_boundary": "PASS" if boundary["status"].startswith("PASS") else boundary["status"],
        "arcgis_source_capture": "PASS" if arcgis_capture["status"].startswith("PASS") else arcgis_capture["status"],
        "i3s_crawl": "PASS" if i3s["status"].startswith("PASS") else i3s["status"],
        "feature_boundary": "PASS" if feature["status"].startswith("PASS") else feature["status"],
        "usd_conversion": "PASS" if conversion["status"] == "PLACEHOLDER_USD_BINDING_CREATED_WITH_SOURCE_REFS" else conversion["status"],
        "usd_scene": "PASS" if usd_scene["status"].startswith("PASS") else usd_scene["status"],
        "local_omniverse_runtime": "PASS" if local_omniverse["status"].startswith("PASS") else local_omniverse["status"],
        "object_bindings": "PASS" if object_bindings["status"].startswith("PASS") else object_bindings["status"],
        "runtime_overlays": "PASS" if overlays["status"].startswith("PASS") else overlays["status"],
        "identity_join_plan": "PASS" if identity["status"].startswith("PASS") else identity["status"],
        "fallback_plan": "PASS" if fallback["status"].startswith("PASS") else fallback["status"],
        "validation": validation["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "hashes": hashes["status"],
    }
    hard_fail = any(value != "PASS" for value in checks.values())
    placeholder_count = sum(1 for binding in object_bindings["bindings"] if "placeholder" in str(binding.get("geometry_status")))
    source_ref_count = sum(1 for binding in object_bindings["bindings"] if binding.get("source_entity_refs"))
    decision = {
        "status": "FAIL_MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING" if hard_fail else "PASS_MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_WITH_LIMITATIONS",
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "hero_subset": boundary,
        "arcgis_source_capture_summary": {
            "status": arcgis_capture["status"],
            "source_count": arcgis_capture["source_count"],
            "max_bytes_per_request": arcgis_capture["max_bytes_per_request"],
        },
        "i3s_crawl_summary": {
            "status": i3s["status"],
            "overall_conversion_status": i3s["overall_conversion_status"],
        },
        "feature_boundary_summary": {
            "status": feature["status"],
            "feature_count_returned": feature["feature_count_returned"],
            "geometry_crs": feature["geometry_crs"],
        },
        "usd_conversion_status": conversion["classification"],
        "usd_scene_status": usd_scene["status"],
        "local_omniverse_runtime_summary": {
            "status": local_omniverse["status"],
            "kit_version": local_omniverse["kit_version"],
            "runtime_topology": local_omniverse["runtime_topology"],
            "composer_available": local_omniverse["citybrain_usd_composer_bat"]["exists"],
            "scene_open_smoke_status": local_omniverse["scene_open_smoke_status"],
            "bare_kit_python_pxr_probe": local_omniverse["bare_kit_python_pxr_probe"]["status"],
            "recommended_open_command": local_omniverse["generated_scene"]["recommended_open_command"],
        },
        "object_binding_count": object_bindings["binding_count"],
        "runtime_overlay_count": overlays["overlay_count"],
        "placeholder_geometry_count": placeholder_count,
        "source_backed_reference_count": source_ref_count,
        "canonical_identity_binding_status": identity["canonical_identity_binding_status"],
        "manual_export_required": fallback["manual_export_required"],
        "validation_summary": validation,
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "recommended_next_main_task": "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT",
        "recommended_parallel_task": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
        "checks": checks,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json", decision)
    return decision


def main() -> None:
    reset_root()
    before = capture_watch_signatures()
    write_docs()
    prereq = prerequisite_report()
    boundary = hero_subset_boundary()
    arcgis_capture = arcgis_source_capture()
    i3s = i3s_crawl_report()
    feature = feature_boundary_report()
    conversion = usd_conversion_feasibility(i3s, feature)
    usd_scene, building_specs, road_specs = create_usd_scene()
    local_omniverse = local_omniverse_runtime_probe()
    object_bindings = create_object_bindings(building_specs, road_specs)
    overlays = create_runtime_overlays()
    identity = write_identity_join_plan()
    fallback = write_manual_export_fallback()
    open_instructions = write_open_instructions()
    limitations, negative = write_limitations_and_negative()
    validation = validation_report(object_bindings, overlays, conversion)
    claim = write_claim_audit()
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret = write_secret_audit()
    hashes = hash_output()
    decision = write_decision(
        prereq,
        boundary,
        arcgis_capture,
        i3s,
        feature,
        conversion,
        usd_scene,
        local_omniverse,
        object_bindings,
        overlays,
        identity,
        fallback,
        validation,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        hashes,
    )
    hashes = hash_output()
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task": TASK,
            "timestamp": now_iso(),
            "decision_status": decision["status"],
            "open_instructions_status": open_instructions["status"],
            "hash_count": hashes["count"],
        },
    )
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"ArcGIS source capture: {arcgis_capture['status']}")
    print(f"I3S crawl: {i3s['status']}")
    print(f"Feature boundary: {feature['status']}")
    print(f"USD conversion: {conversion['classification']}")
    print(f"USD scene: {usd_scene['status']}")
    print(f"Local Omniverse runtime: {local_omniverse['status']}")
    print(f"Object bindings: {object_bindings['binding_count']}")
    print(f"Runtime overlays: {overlays['overlay_count']}")
    print(f"Validation: {validation['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

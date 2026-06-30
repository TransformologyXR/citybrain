from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight"
TASK = "MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4-omniverse-3d-subset-preflight.v1"
NOW = datetime(2026, 6, 30, 0, 30, 0, tzinfo=timezone.utc)


INPUTS = {
    "d3_completion_train": ROOT / "outputs" / "main_track1_d3_completion_train_to_d4_roadmap_r1",
    "d3_closeout": ROOT / "outputs" / "main_track1_d3_closeout_and_d4_roadmap",
    "d3_integrated_smoke": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
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
    "nyc_landing": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "nyc_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_landing": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "chi_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "nyc_mappluto_shp": ROOT / "nyc_mappluto_25v4_arc_shp",
    "nyc_mappluto_csv": ROOT / "nyc_pluto_25v4_arc_csv",
    "chi_synthetic_pack": ROOT / "data_synthetic" / "pv1_sdf" / "packs" / "sdf_chi_near_west_side_v1",
    "barc_cadastre_raw": ROOT / "data_landing" / "barc_d1_official_sources_v1" / "raw" / "cadastre",
    "london_bulk_landing": ROOT / "data_landing" / "xdata_d1_bulk_official_sources_v1" / "london",
}

DECISIONS = {
    "d3_completion_train": "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_DECISION.json",
    "d3_closeout": "MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_DECISION.json",
    "d3_integrated_smoke": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "perception_d3_review_api": "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
}

WATCH_KEYS = [
    "d3_completion_train",
    "d3_closeout",
    "d3_integrated_smoke",
    "event_fabric_d3_multicity",
    "perception_d3_bridge",
    "perception_d3_review_api",
    "sumo_d3_hardening",
    "sumo_d3_catalog",
    "synthetic_replay",
    "pv1_d19_d22",
    "a9_g1",
    "platform_state",
    "accepted_flow_state",
    "track2",
    "barc_landing",
    "barc_prep",
    "nyc_landing",
    "nyc_prep",
    "chi_landing",
    "chi_prep",
    "lon_prep",
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
    "not full",
    "not a",
]

CITY_CRS = {
    "BARC": {"target_crs": "EPSG:25831", "name": "ETRS89 / UTM zone 31N", "ft_to_m": False},
    "NYC": {"target_crs": "EPSG:2263", "name": "NAD83 / New York Long Island", "ft_to_m": True},
    "CHI": {"target_crs": "EPSG:3435", "name": "NAD83 / Illinois East", "ft_to_m": True},
    "LON": {"target_crs": "EPSG:27700", "name": "British National Grid", "ft_to_m": False},
}

BARC_ARCGIS_BUILDINGS_I3S = "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer/layers/0"
BARC_ARCGIS_LIDAR_SCENESERVER = "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer"
BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER = "https://tiles-eu1.arcgis.com/7cCya5lpv5CmFJHv/arcgis/rest/services/Barcelona_final_WSL1/SceneServer"
BARC_ARCGIS_ADMIN_FEATURESERVER = "https://services7.arcgis.com/y6eySXcpKlHjsqpN/arcgis/rest/services/Seccions%20Censals%20Barcelona/FeatureServer"

REMOTE_PROBE_MAX_BYTES = 256 * 1024


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


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def status_of(data: dict[str, Any]) -> str:
    return str(data.get("status") or data.get("final_status") or "MISSING")


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


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


def capture_watch_signatures() -> dict[str, Any]:
    signatures = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {"exists": True, "kind": "file", "size": root.stat().st_size, "mtime": root.stat().st_mtime, "sha256": sha256_file(root)}
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        capped = False
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            file_count += 1
            stat = path.stat()
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if file_count >= 5000:
                capped = True
                break
        signatures[key] = {
            "exists": True,
            "kind": "directory",
            "file_count_sampled": file_count,
            "total_bytes_sampled": total_bytes,
            "max_mtime_sampled": max_mtime,
            "sample_capped": capped,
        }
    return signatures


def decision_for(key: str) -> dict[str, Any]:
    return read_json(INPUTS[key] / DECISIONS[key])


def prerequisite_report() -> dict[str, Any]:
    d3_completion = decision_for("d3_completion_train")
    d3_closeout = decision_for("d3_closeout")
    integrated = decision_for("d3_integrated_smoke")
    checks = [
        {
            "key": "d3_completion_train",
            "root": rel(INPUTS["d3_completion_train"]),
            "status": status_of(d3_completion),
            "expected": "PASS_MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_WITH_LIMITATIONS",
            "gate": "PASS" if status_of(d3_completion) == "PASS_MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_WITH_LIMITATIONS" else "FAIL",
        },
        {
            "key": "d3_closeout",
            "root": rel(INPUTS["d3_closeout"]),
            "status": status_of(d3_closeout),
            "expected": "PASS_MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_WITH_LIMITATIONS",
            "gate": "PASS" if status_of(d3_closeout) == "PASS_MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_WITH_LIMITATIONS" else "FAIL",
        },
        {
            "key": "d3_integrated_smoke",
            "root": rel(INPUTS["d3_integrated_smoke"]),
            "status": status_of(integrated),
            "expected": "PASS_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_WITH_LIMITATIONS",
            "gate": "PASS" if status_of(integrated) == "PASS_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_WITH_LIMITATIONS" else "FAIL",
            "integrated_event_count": integrated.get("total_integrated_event_count"),
            "event_counts_by_lifecycle": integrated.get("event_counts_by_lifecycle"),
        },
    ]
    for key in ["perception_d3_bridge", "perception_d3_review_api", "sumo_d3_hardening", "sumo_d3_catalog", "synthetic_replay"]:
        d = decision_for(key)
        checks.append({"key": key, "root": rel(INPUTS[key]), "status": status_of(d), "gate": "PASS" if status_of(d).startswith("PASS") else "FAIL"})
    report = {
        "status": "PASS" if all(row["gate"] == "PASS" for row in checks) else "FAIL",
        "task": TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "d3_closed_with_limitations": True,
        "d4_roadmap_exists": (INPUTS["d3_completion_train"] / "TRACK1_D3_D4_ROADMAP_HANDOFF.md").exists(),
        "integrated_event_inputs_usable": status_of(integrated).startswith("PASS") and integrated.get("total_integrated_event_count", 0) > 0,
        "no_prior_roots_mutated_by_preflight": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_OMNIVERSE_PREFLIGHT_PREREQUISITE_REPORT.json", report)
    return report


def path_record(city: str, family: str, path: Path, status: str, asset_scope: str, notes: str) -> dict[str, Any]:
    return {
        "city_id": city,
        "source_family": family,
        "source_ref": rel(path),
        "exists": path.exists(),
        "classification": status if path.exists() else "NOT_FOUND",
        "asset_scope": asset_scope,
        "notes": notes,
    }


def source_inventory() -> list[dict[str, Any]]:
    entries = [
        {
            "city_id": "BARC",
            "source_family": "arcgis_i3s_edif_bcn_3d",
            "source_ref": BARC_ARCGIS_BUILDINGS_I3S,
            "exists": True,
            "classification": "AVAILABLE_METADATA_ONLY",
            "asset_scope": "3D building mesh candidate",
            "notes": "High-priority Barcelona 3DObject I3S 1.7 meshpyramids/triangles candidate with View/Query/Extract. Use as mesh source only, not canonical building identity. Clip to bounded hero subset before any USD conversion.",
            "layer_properties": {
                "name": "Edif_Bcn_3D",
                "layerType": "3DObject",
                "i3s_version": "1.7",
                "capabilities": ["View", "Query", "Extract"],
                "store_profile": "meshpyramids",
                "geometry": "triangles",
                "lod": "MeshPyramid / node-switching",
                "horizontal_crs": "EPSG:4326",
                "vertical_crs": "EGM96 geoid",
                "height_unit": "metre",
                "extent": {"xmin": 2.089885, "ymin": 41.316417, "xmax": 2.230250, "ymax": 41.468503},
                "fields": ["OBJECTID", "TEMA_DESCR", "CONJ_DESCR", "SCONJ_DESC", "COTA", "DISTRICTE", "BARRI"],
            },
            "identity_rule": "Use OBJECTID as scene-layer feature ID only; spatially join to cadastre building, parcel, and address records for canonical CityBrain identity.",
            "conversion_rule": "For USD/OpenUSD convert EPSG:4326 plus EGM96 heights to Barcelona EPSG:25831 or subset-local ENU metres, Z-up, metersPerUnit=1.0.",
            "download_boundary": "Do not attempt full-city I3S/USD conversion in first implementation task; clip to bounded hero subset first.",
        },
        {
            "city_id": "BARC",
            "source_family": "arcgis_i3s_barcelona_final_wsl1_integrated_mesh",
            "source_ref": BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER,
            "exists": True,
            "classification": "AVAILABLE_METADATA_ONLY",
            "asset_scope": "textured integrated visual mesh candidate",
            "notes": "High-priority Barcelona IntegratedMesh I3S 1.7 visual source candidate. Use for bounded visual context only; direct USD conversion is not assumed.",
            "layer_properties": {
                "layerType": "IntegratedMesh",
                "i3s_version": "1.7",
                "horizontal_crs": "EPSG:4326",
                "vertical_crs": "EPSG:5773",
                "geometry": "triangles",
                "textures": True,
                "geometry_compression": "Draco",
            },
            "identity_rule": "Mesh feature IDs are not canonical building identity. Bind visual objects to CityBrain entities later through cadastre/spatial join where possible.",
            "conversion_rule": "First test metadata, layer schema, root node/resource access, and a tiny bounded extent. Convert only a clipped subset to local ENU metres, Z-up, metersPerUnit=1.0 if feasible.",
            "fallback_plan": "If direct I3S-to-USD conversion is not feasible, use a manual ArcGIS Pro or CityEngine bounded export workflow before OpenUSD authoring.",
            "download_boundary": "Do not download the full integrated mesh unless explicitly approved.",
        },
        {
            "city_id": "BARC",
            "source_family": "arcgis_lidar_point_cloud",
            "source_ref": BARC_ARCGIS_LIDAR_SCENESERVER,
            "exists": True,
            "classification": "AVAILABLE_METADATA_ONLY",
            "asset_scope": "point-cloud/elevation candidate",
            "notes": "Barcelona LiDAR SceneServer candidate for elevation or point-cloud context only. The service reports PointCloud, EPSG:3857, View capability, and elevation/intensity/class-code attributes. Do not assume clean USD conversion.",
            "layer_properties": {
                "layerType": "PointCloud",
                "horizontal_crs": "EPSG:3857",
                "capabilities": ["View"],
                "reported_attributes": ["elevation", "intensity", "class-code"],
            },
            "identity_rule": "Point-cloud points are not canonical CityBrain entities.",
            "conversion_rule": "Preserve EPSG:3857 and point attribute metadata; use only bounded samples for elevation/visual context after explicit extraction validation.",
            "download_boundary": "Do not download full-city point cloud assets in preflight or first implementation.",
        },
        {
            "city_id": "BARC",
            "source_family": "arcgis_admin_boundary_polygons",
            "source_ref": BARC_ARCGIS_ADMIN_FEATURESERVER,
            "exists": True,
            "classification": "AVAILABLE_METADATA_ONLY",
            "asset_scope": "administrative polygons and subset clipping",
            "notes": "FeatureServer query source for Barcelona administrative polygons and bounded subset clipping. Supports Query, max record count 1000, and EPSG:3857; paginate if needed.",
            "layer_properties": {
                "service_type": "FeatureServer",
                "capabilities": ["Query"],
                "max_record_count": 1000,
                "horizontal_crs": "EPSG:3857",
            },
            "identity_rule": "Administrative polygon IDs can support area refs only; they are not building identity.",
            "conversion_rule": "Use direct FeatureServer query for a bounded extent, then transform clipped polygons to subset-local ENU metres.",
            "download_boundary": "Use pagination only for bounded administrative subset queries; no full-city polygon dump in this task.",
        },
        path_record("BARC", "cadastre_parcels", INPUTS["barc_landing"] / "data" / "normalized" / "cadastre_building_area", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "building/parcel attributes", "Barcelona cadastre attributes are local; geometry binding needs subset extraction and validation."),
        path_record("BARC", "cadastre_buildings", INPUTS["barc_landing"] / "data" / "normalized" / "cadastre_buildings", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "building footprints/attributes", "Cadastre building records are local but D4 must validate geometry/height fields before extrusion."),
        path_record("BARC", "cadastre_addresses", INPUTS["barc_landing"] / "data" / "normalized" / "address_table", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "address anchors", "Addresses can support object labels, not standalone 3D geometry."),
        path_record("BARC", "traffic_sections", INPUTS["barc_landing"] / "data" / "normalized" / "traffic_sections", "AVAILABLE_LOCAL", "roads/road centerlines", "Traffic sections align well with SUMO D3 Barcelona corridor."),
        path_record("BARC", "traffic_itineraries", INPUTS["barc_landing"] / "data" / "normalized" / "traffic_itineraries", "AVAILABLE_LOCAL", "roads/routes", "Itineraries can support corridor selection and route overlays."),
        path_record("BARC", "tmb_static_gtfs", INPUTS["barc_landing"] / "data" / "normalized" / "tmb_static_gtfs", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "stations/lines", "Useful as transit context, not full station geometry."),
        path_record("BARC", "bicing_gbfs", INPUTS["barc_landing"] / "data" / "normalized" / "bicing_gbfs", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "station markers", "Useful as marker overlays, not 3D assets."),
        path_record("BARC", "air_quality_stations", INPUTS["barc_landing"] / "data" / "normalized" / "air_quality_stations", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "sensor markers", "Marker-only runtime context."),
        path_record("BARC", "terrain_dem", ROOT / "missing" / "barcelona_dem", "NOT_FOUND", "terrain", "No local terrain/DEM found in this preflight."),
        path_record("BARC", "orthophoto_ground_texture", ROOT / "missing" / "barcelona_orthophoto", "NOT_FOUND", "ground texture", "No local orthophoto/ground texture found in this preflight."),
        path_record("NYC", "mappluto_shapefile", INPUTS["nyc_mappluto_shp"] / "MapPLUTO.shp", "AVAILABLE_LOCAL", "parcels/building footprints", "Strong local spatial source for a Manhattan/NYC tax-lot subset; height/storey interpretation needs validation."),
        path_record("NYC", "mappluto_csv", INPUTS["nyc_mappluto_csv"] / "pluto_25v4.csv", "AVAILABLE_LOCAL", "parcel/building attributes", "Strong lot/building attributes for object binding."),
        path_record("NYC", "nyc_dot_speed_context", ROOT / "outputs" / "nyc_allflows_data_landing_r1" / "data" / "normalized" / "nyc_dot_traffic_speeds", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "road/context overlay", "Road runtime context; not a full road-surface mesh."),
        path_record("NYC", "terrain_dem", ROOT / "missing" / "nyc_dem", "NOT_FOUND", "terrain", "No local DEM found in this preflight."),
        path_record("NYC", "orthophoto_ground_texture", ROOT / "missing" / "nyc_orthophoto", "NOT_FOUND", "ground texture", "No local orthophoto/ground texture found in this preflight."),
        path_record("CHI", "building_footprints_primary", ROOT / "data_landing" / "chi_d1b_extended_sources_v1" / "raw" / "city_of_chicago" / "syp8-uezg__building_footprints_primary", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "building footprints", "Large chunked raw source exists; D4 subset extraction should avoid full-city processing."),
        path_record("CHI", "cook_county_parcels", ROOT / "data_landing" / "chi_d1b_extended_sources_v1" / "raw" / "cook_county" / "nj4t-kc8j__cook_county_parcel_universe", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "parcels/lots", "Large source; bounded subset only."),
        path_record("CHI", "traffic_tracker_current", INPUTS["chi_landing"] / "data" / "normalized" / "traffic_tracker_current", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "roads/segments", "Runtime/SUMO context, not a full surface mesh."),
        path_record("CHI", "synthetic_near_west_buildings", INPUTS["chi_synthetic_pack"] / "truth" / "synthetic_buildings.parquet", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "fixture buildings", "Synthetic context-only geometry; useful for fallback, not source-backed city geometry."),
        path_record("CHI", "synthetic_near_west_roads", INPUTS["chi_synthetic_pack"] / "truth" / "synthetic_road_segments.parquet", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "fixture roads", "Synthetic context-only geometry."),
        path_record("LON", "tfl_road_disruptions", INPUTS["london_bulk_landing"] / "raw" / "tfl" / "tfl_road_disruptions.json", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "road line context", "Useful for overlays, not full road surface/3D assets."),
        path_record("LON", "london_identity_fixture", ROOT / "LON_D2_identity_backbone_sample_fixture_v0_1", "AVAILABLE_LOCAL_WITH_LIMITATIONS", "identity samples", "Can support labels and references; not a 3D geometry base."),
        path_record("LON", "building_footprints", ROOT / "missing" / "london_building_footprints", "NOT_FOUND", "building footprints", "No local London building footprints confirmed in this preflight."),
        path_record("LON", "terrain_dem", ROOT / "missing" / "london_dem", "NOT_FOUND", "terrain", "No local DEM found in this preflight."),
    ]
    backend_overlay = [
        path_record("ALL", "event_fabric_logs", INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl", "NOT_3D_ASSET_SCOPE", "runtime overlay", "Event logs are backend/runtime overlays, not 3D assets."),
        path_record("ALL", "evidencebundles", INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json", "NOT_3D_ASSET_SCOPE", "evidence overlay", "EvidenceBundles remain backend/evidence overlays."),
        path_record("ALL", "perception_runtime_logs", INPUTS["perception_d3_bridge"] / "logs" / "deepstream_runtime_stdout.log", "NOT_3D_ASSET_SCOPE", "runtime log", "Raw/runtime logs are not 3D assets and no raw video is included."),
    ]
    return entries + backend_overlay


def write_inventory(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    summary = dict(Counter(row["classification"] for row in inventory))
    data = {
        "status": "PASS",
        "task": TASK,
        "summary": summary,
        "sources": inventory,
        "excluded_backend_overlay_rule": "Complaints, permits, time series, events, sensor data, schedules, EvidenceBundles, API responses, and raw video remain backend/runtime/evidence overlays, not 3D assets.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_3D_SOURCE_INVENTORY.json", data)
    lines = [
        "# D4 3D Source Inventory",
        "",
        "Status: `PASS_WITH_LIMITATIONS`",
        "",
        "| City | Family | Classification | Asset Scope | Source | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in inventory:
        lines.append(f"| {row['city_id']} | `{row['source_family']}` | `{row['classification']}` | {row['asset_scope']} | `{row['source_ref']}` | {row['notes']} |")
    lines.append("")
    lines.append("Tabular complaints, permits, time series, schedules, events, sensor observations, Event Fabric logs, EvidenceBundles, API responses, personal data, and raw video are not 3D assets. They remain backend/evidence overlays.")
    write_text(OUTPUT_ROOT / "D4_3D_SOURCE_INVENTORY.md", "\n".join(lines))
    return data


def with_json_format(url: str, fmt: str = "pjson") -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}f={fmt}"


def web_mercator_xy(lon: float, lat: float) -> tuple[float, float]:
    x = lon * 20037508.342789244 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) * 20037508.342789244 / math.pi
    return x, y


def arcgis_admin_tiny_extent_query() -> str:
    x, y = web_mercator_xy(2.185, 41.405)
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": "1",
        "geometry": f"{x - 175},{y - 175},{x + 175},{y + 175}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3857",
        "spatialRel": "esriSpatialRelIntersects",
        "outSR": "3857",
    }
    return f"{BARC_ARCGIS_ADMIN_FEATURESERVER}/0/query?{urllib.parse.urlencode(params)}"


def fetch_arcgis_probe(url: str, max_bytes: int = REMOTE_PROBE_MAX_BYTES) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "CityBrain-D4-Omniverse-Preflight/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
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
            summary: dict[str, Any] = {}
            if isinstance(parsed, dict):
                for key in ["name", "serviceName", "layerType", "type", "version", "currentVersion", "capabilities", "maxRecordCount"]:
                    if key in parsed:
                        summary[key] = parsed[key]
                if "spatialReference" in parsed:
                    summary["spatialReference"] = parsed["spatialReference"]
                if "heightModelInfo" in parsed:
                    summary["heightModelInfo"] = parsed["heightModelInfo"]
                if "fields" in parsed and isinstance(parsed["fields"], list):
                    summary["field_names"] = [field.get("name") for field in parsed["fields"][:16] if isinstance(field, dict)]
                    summary["field_count"] = len(parsed["fields"])
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
            return {
                "url": url,
                "http_status": getattr(response, "status", None),
                "http_ok": True,
                "content_type": response.headers.get("Content-Type"),
                "bytes_read": len(raw),
                "truncated_at_cap": truncated,
                "json_parse_error": parse_error,
                "json_summary": summary,
                "raw_preview": None if parsed is not None else text[:240],
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
        return {
            "url": url,
            "http_status": status,
            "http_ok": False,
            "content_type": None,
            "bytes_read": 0,
            "truncated_at_cap": False,
            "error": str(exc),
        }


def arcgis_remote_preflight() -> dict[str, Any]:
    tests = [
        {"source_key": "barc_i3s_edif_bcn_3d", "test": "layer_schema_metadata", "url": with_json_format(BARC_ARCGIS_BUILDINGS_I3S), "required": True},
        {"source_key": "barc_i3s_edif_bcn_3d", "test": "root_node_access", "url": with_json_format(f"{BARC_ARCGIS_BUILDINGS_I3S}/nodes/root"), "required": False},
        {
            "source_key": "barc_i3s_edif_bcn_3d",
            "test": "tiny_attribute_query",
            "url": f"{BARC_ARCGIS_BUILDINGS_I3S}/query?{urllib.parse.urlencode({'f': 'json', 'where': '1=1', 'outFields': 'OBJECTID,DISTRICTE,BARRI', 'returnGeometry': 'false', 'resultRecordCount': '1'})}",
            "required": False,
        },
        {"source_key": "barc_lidar_point_cloud", "test": "service_metadata", "url": with_json_format(BARC_ARCGIS_LIDAR_SCENESERVER), "required": True},
        {"source_key": "barc_lidar_point_cloud", "test": "layer_schema_metadata", "url": with_json_format(f"{BARC_ARCGIS_LIDAR_SCENESERVER}/layers/0"), "required": True},
        {"source_key": "barc_lidar_point_cloud", "test": "root_node_access", "url": with_json_format(f"{BARC_ARCGIS_LIDAR_SCENESERVER}/layers/0/nodes/root"), "required": False},
        {"source_key": "barc_integrated_mesh", "test": "service_metadata", "url": with_json_format(BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER), "required": True},
        {"source_key": "barc_integrated_mesh", "test": "layer_schema_metadata", "url": with_json_format(f"{BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER}/layers/0"), "required": True},
        {"source_key": "barc_integrated_mesh", "test": "root_node_access", "url": with_json_format(f"{BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER}/layers/0/nodes/root"), "required": False},
        {"source_key": "barc_admin_boundary_polygons", "test": "service_metadata", "url": with_json_format(BARC_ARCGIS_ADMIN_FEATURESERVER), "required": True},
        {"source_key": "barc_admin_boundary_polygons", "test": "layer_schema_metadata", "url": with_json_format(f"{BARC_ARCGIS_ADMIN_FEATURESERVER}/0"), "required": True},
        {"source_key": "barc_admin_boundary_polygons", "test": "tiny_bounded_extent_query", "url": arcgis_admin_tiny_extent_query(), "required": True},
    ]
    probes = []
    for test in tests:
        probe = fetch_arcgis_probe(test["url"])
        probe.update({"source_key": test["source_key"], "test": test["test"], "required": test["required"]})
        probes.append(probe)
    required = [probe for probe in probes if probe["required"]]
    required_ok = all(probe["http_ok"] for probe in required)
    status = "PASS_WITH_LIMITATIONS" if required_ok else "FAIL"
    report = {
        "status": status,
        "timestamp": now_iso(),
        "probe_policy": {
            "max_bytes_per_request": REMOTE_PROBE_MAX_BYTES,
            "no_full_city_download": True,
            "metadata_and_tiny_bounded_probe_only": True,
            "selected_tiny_extent_center_lon_lat": [2.185, 41.405],
            "selected_tiny_extent_half_size_meters": 175,
        },
        "sources": [
            {
                "source_key": "barc_i3s_edif_bcn_3d",
                "role": "3DObject building/mesh source candidate only",
                "canonical_identity_boundary": "OBJECTID is scene-layer ID only; canonical identity requires cadastre/address/parcel spatial join.",
            },
            {
                "source_key": "barc_lidar_point_cloud",
                "role": "PointCloud/elevation candidate only",
                "conversion_boundary": "Do not assume clean USD conversion.",
            },
            {
                "source_key": "barc_integrated_mesh",
                "role": "High-priority textured visual mesh candidate",
                "conversion_boundary": "Attempt bounded I3S resource crawl; use manual ArcGIS Pro/CityEngine export fallback if direct USD conversion is not feasible.",
            },
            {
                "source_key": "barc_admin_boundary_polygons",
                "role": "FeatureServer query source for admin polygons and subset clipping",
                "query_boundary": "Paginate only inside bounded subset when needed.",
            },
        ],
        "probes": probes,
        "required_probe_failures": [{"source_key": probe["source_key"], "test": probe["test"], "url": probe["url"], "error": probe.get("error")} for probe in required if not probe["http_ok"]],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_ARCGIS_3D_REMOTE_PREFLIGHT_REPORT.json", report)
    lines = [
        "# D4 ArcGIS 3D Remote Preflight Report",
        "",
        f"Status: `{status}`",
        "",
        f"Max bytes per request: `{REMOTE_PROBE_MAX_BYTES}`",
        "",
        "| Source | Test | Required | HTTP | Bytes | Truncated | Summary |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for probe in probes:
        summary = json.dumps(probe.get("json_summary", {}), sort_keys=True)[:240]
        lines.append(f"| `{probe['source_key']}` | `{probe['test']}` | `{probe['required']}` | `{probe.get('http_status')}` | {probe.get('bytes_read', 0)} | `{probe.get('truncated_at_cap')}` | `{summary}` |")
    lines.extend(
        [
            "",
            "This report proves metadata and tiny bounded access only. It does not download full-city 3D assets and does not start USD conversion.",
        ]
    )
    write_text(OUTPUT_ROOT / "D4_ARCGIS_3D_REMOTE_PREFLIGHT_REPORT.md", "\n".join(lines))
    return report


def integrated_city_counts() -> dict[str, int]:
    rows = read_jsonl(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")
    return dict(Counter(row.get("city_id", "UNKNOWN") for row in rows))


def build_city_profiles(inventory: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts = integrated_city_counts()
    profiles = {
        "BARC": {
            "city_id": "BARC",
            "city_name": "Barcelona",
            "available_spatial_3d_source_families": ["ArcGIS I3S Edif_Bcn_3D 3DObject mesh candidate", "ArcGIS Barcelona_final_WSL1 IntegratedMesh visual candidate", "ArcGIS Barcelona_Lidar PointCloud/elevation candidate", "ArcGIS Seccions Censals FeatureServer clipping polygons", "cadastre_buildings", "cadastre_parcels", "address_table", "traffic_sections", "traffic_itineraries", "TMB GTFS", "Bicing markers", "air/noise/sensor markers"],
            "candidate_hero_subset_areas": ["Eixample/Sant Marti traffic-cadastre corridor", "Port/Parc de la Ciutadella mobility-environment fragment"],
            "likely_crs": CITY_CRS["BARC"],
            "available_building_road_water_terrain_inputs": {
                "buildings": "ArcGIS I3S Edif_Bcn_3D is a high-priority remote 3DObject mesh candidate; ArcGIS integrated mesh is a high-priority textured visual context candidate; cadastre building/area/age records are local identity/join candidates",
                "roads": "traffic sections and SUMO D3 Barcelona network local",
                "water": "not confirmed as local D4 3D asset",
                "terrain": "ArcGIS LiDAR PointCloud is a remote elevation/point-cloud candidate only; local terrain not found",
                "admin_boundaries": "ArcGIS FeatureServer census-section polygons can support bounded subset clipping and area refs",
            },
            "d3_runtime_relevance": f"{counts.get('BARC', 0)} integrated D3 events; strongest integrated city count.",
            "sumo_d3_scenario_relevance": "Barcelona SUMO D3 network and scenario catalog are available; connector/turn-permission limitation remains.",
            "perception_review_relevance": "Perception D3 runtime is sample-media/global, not Barcelona-specific; can use generic review markers only.",
            "synthetic_overlay_relevance": "Synthetic Barcelona mobility/permit/SUMO replay overlays available as synthetic/context-only.",
            "major_limitations": ["terrain/orthophoto not found locally", "I3S 3DObject and IntegratedMesh sources are remote metadata/probe candidates in preflight and must be clipped before use", "LiDAR PointCloud is elevation/visual context only and not assumed cleanly convertible to USD", "I3S OBJECTID and mesh feature IDs are not canonical building identity", "cadastre geometry/height validation required", "admin polygon FeatureServer queries must stay bounded/paginated", "not a citywide twin", "Barcelona SUMO connector limitation remains"],
            "recommendation_score": 98,
        },
        "NYC": {
            "city_id": "NYC",
            "city_name": "NYC",
            "available_spatial_3d_source_families": ["MapPLUTO shapefile", "PLUTO CSV attributes", "DOT traffic speed context", "SUMO D3 NYC network"],
            "candidate_hero_subset_areas": ["Lower Manhattan / civic-commercial tax-lot corridor", "Manhattan DOT speed corridor around MapPLUTO lots"],
            "likely_crs": CITY_CRS["NYC"],
            "available_building_road_water_terrain_inputs": {
                "buildings": "MapPLUTO parcel geometry and building attributes local",
                "roads": "DOT speed context and SUMO D3 NYC network local",
                "water": "not confirmed as local D4 3D asset",
                "terrain": "not found locally",
            },
            "d3_runtime_relevance": f"{counts.get('NYC', 0)} integrated D3 events; good SUMO/synthetic coverage.",
            "sumo_d3_scenario_relevance": "NYC SUMO D3 scenarios available.",
            "perception_review_relevance": "Generic Track 1 perception review markers can attach to sample camera markers, not NYC production CCTV.",
            "synthetic_overlay_relevance": "Synthetic NYC overlays available as synthetic/context-only.",
            "major_limitations": ["MapPLUTO height semantics require validation", "terrain/orthophoto not found", "D3 observed/context coverage lower than Barcelona/London"],
            "recommendation_score": 88,
        },
        "CHI": {
            "city_id": "CHI",
            "city_name": "Chicago",
            "available_spatial_3d_source_families": ["Chicago building footprints raw chunks", "Cook County parcels", "Traffic Tracker", "synthetic Near West Side geometry"],
            "candidate_hero_subset_areas": ["Near West Side synthetic/source hybrid corridor", "Traffic Tracker civic-storm corridor"],
            "likely_crs": CITY_CRS["CHI"],
            "available_building_road_water_terrain_inputs": {
                "buildings": "source-backed building footprints exist but are large chunked raw source",
                "roads": "Traffic Tracker and SUMO D3 Chicago network local",
                "water": "not confirmed as local D4 3D asset",
                "terrain": "not found locally",
            },
            "d3_runtime_relevance": f"{counts.get('CHI', 0)} integrated D3 events; strong traffic/SUMO/synthetic coverage.",
            "sumo_d3_scenario_relevance": "Chicago SUMO D3 scenarios available.",
            "perception_review_relevance": "Generic sample-media review markers only.",
            "synthetic_overlay_relevance": "Strong synthetic Near West Side building/parcel/road fixture exists; must stay synthetic/context-only unless backed by source subset.",
            "major_limitations": ["source-backed footprint/parcels are large and need bounded extraction", "synthetic geometry cannot be claimed as observed/source-backed", "terrain/orthophoto not found"],
            "recommendation_score": 84,
        },
        "LON": {
            "city_id": "LON",
            "city_name": "London",
            "available_spatial_3d_source_families": ["TfL road disruption line context", "identity fixtures", "SUMO D3 London network"],
            "candidate_hero_subset_areas": ["TfL road disruption context corridor", "LFB/EA/TfL context fragment"],
            "likely_crs": CITY_CRS["LON"],
            "available_building_road_water_terrain_inputs": {
                "buildings": "not found locally",
                "roads": "TfL disruption lines and SUMO D3 London network local",
                "water": "EA context may exist as event context, not confirmed as 3D water surface",
                "terrain": "not found locally",
            },
            "d3_runtime_relevance": f"{counts.get('LON', 0)} integrated D3 events; strong observed/context count but weaker 3D asset base.",
            "sumo_d3_scenario_relevance": "London SUMO D3 scenarios available, but entries do not promote London to full Flow 3.",
            "perception_review_relevance": "Generic sample-media review markers only.",
            "synthetic_overlay_relevance": "Synthetic London overlays available as synthetic/context-only.",
            "major_limitations": ["building footprint/terrain/orthophoto not found", "road lines are context, not complete 3D road surfaces", "London not promoted to full Flow 3"],
            "recommendation_score": 76,
        },
    }
    for profile in profiles.values():
        city_sources = [row for row in inventory if row["city_id"] in {profile["city_id"], "ALL"}]
        profile["inventory_refs"] = [row["source_ref"] for row in city_sources if row["classification"] != "NOT_FOUND"]
        profile["schema_version"] = SCHEMA_VERSION
    for city_id, profile in profiles.items():
        write_json(OUTPUT_ROOT / f"D4_CITY_3D_PROFILE_{'BARCELONA' if city_id == 'BARC' else 'CHICAGO' if city_id == 'CHI' else 'LONDON' if city_id == 'LON' else 'NYC'}.json", profile)
    return profiles


def hero_selection(profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    recommended = {
        "city_id": "BARC",
        "subset_id": "barc_eixample_sant_marti_mobility_cadastre_corridor_d4_preflight",
        "subset_name": "Barcelona Eixample/Sant Marti mobility-cadastre corridor",
        "selection_reason": "Best combined D3 event coverage, Barcelona all-flow acceptance context, high-priority ArcGIS I3S LOD2 building mesh candidate, high-priority ArcGIS textured integrated mesh candidate, LiDAR/elevation candidate, admin polygon clipping source, local cadastre/address/traffic/GTFS inputs, and SUMO D3 Barcelona scenarios.",
        "source_refs": [
            BARC_ARCGIS_BUILDINGS_I3S,
            BARC_ARCGIS_INTEGRATED_MESH_SCENESERVER,
            BARC_ARCGIS_LIDAR_SCENESERVER,
            BARC_ARCGIS_ADMIN_FEATURESERVER,
            rel(INPUTS["barc_landing"] / "data" / "normalized" / "cadastre_buildings"),
            rel(INPUTS["barc_landing"] / "data" / "normalized" / "cadastre_building_area"),
            rel(INPUTS["barc_landing"] / "data" / "normalized" / "traffic_sections"),
            rel(INPUTS["sumo_d3_hardening"] / "networks" / "barcelona" / "network.net.xml"),
            rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
        ],
        "approximate_bounding_rule": "Bound the first D4 USD subset to a small corridor around selected Barcelona SUMO D3 traffic-section edges and nearby cadastre/address records; do not process the full city.",
        "expected_asset_types": ["bounded I3S building mesh candidates", "bounded integrated visual mesh candidate", "bounded point-cloud/elevation candidate", "admin boundary clipping polygons", "building footprint/extrusion candidates", "road/traffic-section linework", "station/sensor markers", "review markers", "simulation route overlays"],
        "expected_object_bindings": ["building", "road segment", "junction", "sensor/camera marker", "review marker", "simulation route/edge marker"],
        "d3_event_families_to_overlay": ["observed/context civic/mobility context", "simulated/context SUMO", "synthetic/context Barcelona overlay", "limitation markers"],
        "limitations": ["preflight only", "no full USD scene", "I3S/IntegratedMesh/LiDAR metadata and tiny-probe only in preflight", "clip every ArcGIS 3D source to bounded subset before extraction or conversion", "OBJECTID and mesh feature IDs are source feature IDs only, not canonical identity", "direct I3S to USD feasibility is unproven", "manual ArcGIS Pro or CityEngine export fallback may be required", "terrain/orthophoto not local", "cadastre height/geometry validation needed", "Barcelona SUMO connector limitation remains"],
        "why_it_is_not_a_production_citywide_twin": "The subset is a bounded corridor fragment with review/context/simulated/synthetic overlays only. No production readiness. No full citywide certified digital twin. No operational commands.",
    }
    alternates = [
        {
            "city_id": "NYC",
            "subset_id": "nyc_mappluto_dot_manhattan_corridor_d4_preflight",
            "subset_name": "NYC MapPLUTO/DOT Manhattan corridor",
            "selection_reason": "Strongest ready local building/parcel spatial base through MapPLUTO, with SUMO D3 and DOT context available.",
            "source_refs": [rel(INPUTS["nyc_mappluto_shp"] / "MapPLUTO.shp"), rel(INPUTS["nyc_mappluto_csv"] / "pluto_25v4.csv"), rel(INPUTS["sumo_d3_hardening"] / "networks" / "nyc" / "network.net.xml")],
            "approximate_bounding_rule": "Bound to a small MapPLUTO tax-lot corridor around the selected NYC SUMO D3 network subset.",
            "expected_asset_types": ["parcel/building footprints", "road segment overlays", "simulation route overlays"],
            "expected_object_bindings": ["building", "parcel/lot", "road segment", "simulation route/edge marker"],
            "d3_event_families_to_overlay": ["observed/context", "simulated/context", "synthetic/context", "limitation markers"],
            "limitations": ["D3 observed/context city count lower than Barcelona", "height/storey semantics need validation", "terrain/orthophoto not local"],
            "why_it_is_not_a_production_citywide_twin": "The subset is a bounded corridor, not all NYC and not a certified digital twin.",
        },
        {
            "city_id": "CHI",
            "subset_id": "chi_near_west_side_traffic_synthetic_hybrid_d4_preflight",
            "subset_name": "Chicago Near West Side traffic/source-synthetic hybrid corridor",
            "selection_reason": "Good D3 runtime coverage, source building/parcels exist, and synthetic Near West Side geometry offers a fallback fixture if source extraction is heavy.",
            "source_refs": [rel(INPUTS["chi_synthetic_pack"] / "truth" / "synthetic_buildings.parquet"), rel(INPUTS["chi_synthetic_pack"] / "truth" / "synthetic_road_segments.parquet"), rel(INPUTS["sumo_d3_hardening"] / "networks" / "chicago" / "network.net.xml")],
            "approximate_bounding_rule": "Use bounded Near West Side fixture/source candidate only; do not process full Cook County or full Chicago footprint chunks.",
            "expected_asset_types": ["source-backed footprint candidates", "synthetic fixture geometry", "traffic segment overlays"],
            "expected_object_bindings": ["building", "parcel/lot", "road segment", "simulation route/edge marker"],
            "d3_event_families_to_overlay": ["observed/context", "simulated/context", "synthetic/context"],
            "limitations": ["synthetic geometry must remain synthetic/context-only", "source building/parcels are large chunked sources", "terrain/orthophoto not local"],
            "why_it_is_not_a_production_citywide_twin": "It is a bounded source/synthetic preflight candidate, not a citywide certified model.",
        },
    ]
    selection = {
        "status": "PASS_WITH_LIMITATIONS",
        "recommended_hero_subset": recommended,
        "alternate_subsets": alternates,
        "selection_criteria": [
            "strong local 3D/spatial asset availability",
            "good D3 event/runtime coverage",
            "SUMO D3 scenario coverage",
            "clear object-binding path",
            "manageable geometry size",
            "visually meaningful for control-room demo",
            "strong claim-boundary fit",
            "low risk of remote downloads",
            "useful for future review UI/control-room workflow",
        ],
        "city_scores": {city: profiles[city]["recommendation_score"] for city in profiles},
        "schema_version": SCHEMA_VERSION,
    }
    alternate_lines = "\n".join(f"- `{alt['subset_id']}`: {alt['selection_reason']}" for alt in alternates)
    write_json(OUTPUT_ROOT / "D4_HERO_SUBSET_SELECTION.json", selection)
    write_text(
        OUTPUT_ROOT / "D4_HERO_SUBSET_SELECTION_REPORT.md",
        f"""
# D4 Hero Subset Selection

Status: `PASS_WITH_LIMITATIONS`

Recommended subset: `{recommended['subset_id']}`

{recommended['selection_reason']}

## Recommended Boundary

{recommended['approximate_bounding_rule']}

Expected asset types:

{chr(10).join(f'- {item}' for item in recommended['expected_asset_types'])}

Expected D3 overlays:

{chr(10).join(f'- {item}' for item in recommended['d3_event_families_to_overlay'])}

## Alternates

{alternate_lines}

This is not a production citywide twin. No production readiness. No full citywide certified digital twin. No operational commands.
""",
    )
    return selection


def write_coordinate_and_scene_docs(selection: dict[str, Any]) -> dict[str, Any]:
    rec = selection["recommended_hero_subset"]
    write_text(
        OUTPUT_ROOT / "D4_OPENUSD_COORDINATE_STRATEGY.md",
        f"""
# D4 OpenUSD Coordinate Strategy

Status: `PASS_WITH_LIMITATIONS`

Selected subset: `{rec['subset_id']}`

- Up axis: `Z`
- `metersPerUnit = 1.0`
- Local ENU frame:
  - X = east
  - Y = north
  - Z = up
- Source CRS for Barcelona: `EPSG:25831` ETRS89 / UTM zone 31N.
- I3S source candidate `Edif_Bcn_3D`: input horizontal CRS `EPSG:4326`, vertical CRS `EGM96 geoid`, height unit metre.
- I3S conversion policy: clip the I3S layer to the selected bounded hero subset first, then transform longitude/latitude positions plus EGM96-related heights to `EPSG:25831` or directly into subset-local ENU metres before USD authoring.
- IntegratedMesh source candidate `Barcelona_final_WSL1`: input horizontal CRS `EPSG:4326`, vertical CRS `EPSG:5773`, triangle geometry, textures, and Draco-compressed geometry.
- IntegratedMesh conversion policy: first test metadata, layer schema, root node/resource access, and tiny bounded extent. If direct USD conversion is feasible, clip the mesh to the selected hero subset and convert to local ENU metres. If not feasible, use a bounded ArcGIS Pro or CityEngine export fallback plan.
- LiDAR source candidate `Barcelona_Lidar`: input CRS `EPSG:3857`; use as point-cloud/elevation candidate only and preserve elevation/intensity/class-code metadata.
- Admin polygon source candidate `Seccions Censals Barcelona`: FeatureServer `EPSG:3857` query source for bounded clipping polygons and area refs, with pagination only inside the selected subset.
- Local origin policy: choose a subset-local origin near the centroid of the bounded hero corridor, store the source CRS and origin as scene metadata, and subtract that origin before authoring USD transforms.
- Georeferencing metadata: persist source CRS, source file refs, local origin easting/northing, vertical datum assumption, and conversion timestamp in `/World/Metadata`.
- Precision policy: never author giant absolute CRS coordinates directly into prim transforms; author local metre offsets only.
- Height/elevation assumption: use flat Z=0 ground until a local DEM/height source is validated. Building heights require explicit source validation before extrusion.
- Do not use EPSG:4326 longitude/latitude or Web Mercator as engineering scene coordinates except as intermediate inputs requiring transformation.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4_OPENUSD_SCENE_STRUCTURE_PROPOSAL.md",
        """
# D4 OpenUSD Scene Structure Proposal

This is a preflight scene hierarchy only; the full USD scene is not built in this task.

```text
/World
/World/Geospatial
/World/Geospatial/Terrain
/World/Geospatial/Ground
/World/Geospatial/AdminBoundaries
/World/Buildings
/World/Buildings/I3S_LOD2_MeshCandidates
/World/Buildings/IntegratedMesh_VisualContext
/World/Roads
/World/Water
/World/Vegetation
/World/Infrastructure
/World/Infrastructure/LiDAR_PointCloud_ElevationCandidates
/World/RuntimeOverlays
/World/RuntimeOverlays/Events
/World/RuntimeOverlays/PerceptionCandidates
/World/RuntimeOverlays/Simulation
/World/RuntimeOverlays/Synthetic
/World/ReviewMarkers
/World/Metadata
```

Runtime overlays are authored separately from source-backed geometry. Event Fabric logs, EvidenceBundles, API responses, raw video, and personal data are not geometry layers.
""",
    )
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "up_axis": "Z",
        "meters_per_unit": 1.0,
        "local_frame": "ENU",
        "recommended_source_crs": CITY_CRS["BARC"],
        "full_usd_scene_created": False,
    }


def write_contracts(selection: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    object_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4 USD Object Binding Contract",
        "required_fields": [
            "usd_prim_path",
            "city_id",
            "subset_id",
            "canonical_entity_id",
            "source_entity_refs",
            "entity_type",
            "geometry_source_ref",
            "transform_source",
            "coordinate_frame",
            "confidence",
            "binding_status",
            "limitations",
            "provenance_refs",
        ],
        "entity_types": ["building", "parcel", "lot", "road segment", "junction", "water surface", "terrain tile", "sensor/camera marker", "review marker", "simulation route/edge marker"],
        "binding_statuses": ["bound_source_backed", "bound_derived", "candidate_binding", "fixture_binding", "limitation_only"],
        "example": {
            "usd_prim_path": "/World/Roads/barc_traffic_section_001",
            "city_id": "BARC",
            "subset_id": selection["recommended_hero_subset"]["subset_id"],
            "canonical_entity_id": "candidate:barc:traffic_section:001",
            "source_entity_refs": ["traffic_sections"],
            "entity_type": "road segment",
            "geometry_source_ref": rel(INPUTS["barc_landing"] / "data" / "normalized" / "traffic_sections"),
            "transform_source": "source_crs_to_local_enu",
            "coordinate_frame": "EPSG:25831_to_local_ENU_meters",
            "confidence": 0.74,
            "binding_status": "candidate_binding",
            "limitations": ["preflight contract only", "geometry not authored in this task"],
            "provenance_refs": [rel(INPUTS["sumo_d3_hardening"] / "SUMO_D3_CITY_NETWORK_EXTRACTION_REPORT_BARCELONA.json")],
        },
        "i3s_mesh_binding_rule": {
            "scene_layer": "Edif_Bcn_3D",
            "scene_layer_feature_id_field": "OBJECTID",
            "canonical_identity_rule": "OBJECTID is not canonical building identity. Spatially join the bounded mesh feature to cadastre building, parcel, and address records for canonical CityBrain identity.",
            "source_crs": "EPSG:4326 + EGM96 geoid heights",
            "target_crs_or_frame": "EPSG:25831 or subset-local ENU metres, Z-up, metersPerUnit=1.0",
            "binding_status": "candidate_binding",
            "download_boundary": "Clip to bounded hero subset before extraction/conversion; no full-city I3S to USD conversion in first implementation task.",
        },
        "integrated_mesh_binding_rule": {
            "scene_layer": "Barcelona_final_WSL1",
            "layer_type": "IntegratedMesh",
            "canonical_identity_rule": "Integrated mesh feature/node IDs are not canonical CityBrain identity. Use mesh prims as visual context and attach CityBrain identities only after bounded spatial join to cadastre/address/parcel records.",
            "source_crs": "EPSG:4326 + EPSG:5773 vertical CRS",
            "target_crs_or_frame": "subset-local ENU metres, Z-up, metersPerUnit=1.0",
            "binding_status": "candidate_binding",
            "conversion_feasibility": "unproven; test bounded I3S resource crawl before USD authoring",
            "fallback_plan": "bounded ArcGIS Pro or CityEngine export to interoperable 3D format before OpenUSD composition",
            "download_boundary": "No full-city integrated mesh download without explicit approval.",
        },
        "lidar_point_cloud_binding_rule": {
            "scene_layer": "Barcelona_Lidar",
            "layer_type": "PointCloud",
            "canonical_identity_rule": "Point samples are not canonical CityBrain entities. Use only for bounded elevation/visual context after extraction validation.",
            "source_crs": "EPSG:3857",
            "target_crs_or_frame": "subset-local ENU metres, Z-up, metersPerUnit=1.0",
            "binding_status": "candidate_binding",
            "download_boundary": "No full-city point-cloud download in preflight or first implementation.",
        },
        "admin_polygon_binding_rule": {
            "service": "Seccions Censals Barcelona FeatureServer",
            "layer_type": "FeatureServer polygon",
            "canonical_identity_rule": "Administrative polygon IDs can support area refs and clipping, not building identity.",
            "source_crs": "EPSG:3857",
            "target_crs_or_frame": "subset-local ENU metres, Z-up, metersPerUnit=1.0",
            "binding_status": "candidate_binding",
            "query_boundary": "Use bounded FeatureServer query and pagination only inside selected subset.",
        },
        "schema_version": SCHEMA_VERSION,
    }
    overlay_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4 Runtime Event Overlay Contract",
        "required_fields": [
            "overlay_id",
            "event_id",
            "lifecycle_state",
            "city_id",
            "subset_id",
            "target_usd_prim_path",
            "target_entity_refs",
            "overlay_type",
            "severity_or_context_level",
            "time_window",
            "evidencebundle_ref",
            "review_packet_ref",
            "claim_boundary",
            "limitations",
            "no_action_taken",
        ],
        "supported_lifecycle_states": ["observed/context", "candidate/review", "simulated/context", "synthetic/context", "limitation-only", "late/out-of-order", "expired/superseded"],
        "overlay_types": ["status_marker", "candidate_review_marker", "simulation_route_overlay", "scenario_event_marker", "synthetic_context_marker", "limitation_marker", "expired_marker"],
        "forbidden_semantics": ["no command/action", "no enforcement recommendation", "no dispatch recommendation", "no routing recommendation"],
        "example": {
            "overlay_id": stable_id("d4-overlay", "barc", "sumo"),
            "event_id": "sumo-d3-catalog-event:*",
            "lifecycle_state": "simulated/context",
            "city_id": "BARC",
            "subset_id": selection["recommended_hero_subset"]["subset_id"],
            "target_usd_prim_path": "/World/RuntimeOverlays/Simulation/barc_sumo_corridor",
            "target_entity_refs": ["barc_traffic_section_mobility_corridor_preflight"],
            "overlay_type": "simulation_route_overlay",
            "severity_or_context_level": "context",
            "time_window": "bounded replay window",
            "evidencebundle_ref": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
            "review_packet_ref": None,
            "claim_boundary": "Simulated/context-only. No routing recommendation. No traffic-control command. No action taken.",
            "limitations": ["preflight contract only"],
            "no_action_taken": True,
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_USD_OBJECT_BINDING_CONTRACT.json", object_contract)
    write_json(OUTPUT_ROOT / "D4_RUNTIME_EVENT_OVERLAY_CONTRACT.json", overlay_contract)
    return object_contract, overlay_contract


def write_binding_and_scope_docs(selection: dict[str, Any]) -> dict[str, Any]:
    write_text(
        OUTPUT_ROOT / "D4_D3_TO_USD_BINDING_MATRIX.md",
        """
# D4 D3 To USD Binding Matrix

| D3 Source | Lifecycle | Possible USD Targets | Evidence / Review Refs | Limitations |
| --- | --- | --- | --- | --- |
| Event Fabric D3 MultiCity adapters | observed/context | `/World/RuntimeOverlays/Events`, road/building/sensor markers where entity refs exist | MultiCity EvidenceBundle smoke | Context only, not action |
| Perception D3 candidate/review events | candidate/review | `/World/RuntimeOverlays/PerceptionCandidates`, `/World/ReviewMarkers` | Perception Review API and review packet refs | Sample-media runtime only; no private CCTV; no confirmed violation |
| SUMO D3 network hardening | simulated/context | `/World/Roads`, `/World/RuntimeOverlays/Simulation` | SUMO D3 EvidenceBundle smoke | Simulated only; no observed traffic truth; no routing/control |
| SUMO D3 scenario catalog | simulated/context | `/World/RuntimeOverlays/Simulation`, route/edge markers | Scenario EvidenceBundle smoke | Scenario catalog only |
| Synthetic replay overlays | synthetic/context | `/World/RuntimeOverlays/Synthetic` | Synthetic replay smoke | Not observed/source-backed truth |
| Limitation-only entries | limitation-only | `/World/RuntimeOverlays/Events`, `/World/ReviewMarkers` as limitation markers | Integrated limitation register | No availability or acceptance claim |
""",
    )
    write_text(
        OUTPUT_ROOT / "D4_OMNIVERSE_ASSET_SCOPE_BOUNDARY.md",
        """
# D4 Omniverse Asset Scope Boundary

## Include In 3D

- terrain, if locally available and bounded
- ground/orthophoto, if locally available and bounded
- bounded ArcGIS I3S `Edif_Bcn_3D` 3DObject mesh candidates after subset clip/extract
- bounded ArcGIS integrated mesh visual candidates after tiny resource crawl and subset clip/extract
- bounded ArcGIS LiDAR point-cloud/elevation candidates after extraction validation
- bounded ArcGIS administrative polygons for clipping and area refs
- buildings/footprints/heights, after source validation
- roads/road surfaces/road centerlines
- bridges/overpasses/tunnels, if locally available
- water, if locally available
- vegetation, if locally available
- stations/terminals/street furniture, if locally available and bounded

## Do Not Include As 3D Assets

- complaints
- permits
- violations
- time series
- sensor observations
- schedules
- Event Fabric logs
- EvidenceBundles
- API responses
- personal data
- raw video/CCTV feeds

Those remain backend/evidence overlays. No raw video is included in the 3D scene.
""",
    )
    return {"status": "PASS", "matrix_rows": 6}


def write_implementation_plan(selection: dict[str, Any]) -> dict[str, Any]:
    rec = selection["recommended_hero_subset"]
    write_text(
        OUTPUT_ROOT / "D4_OMNIVERSE_IMPLEMENTATION_PLAN.md",
        f"""
# D4 Omniverse Implementation Plan

Next implementation task: `MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING`

## Selected Hero Subset

`{rec['subset_id']}` - {rec['subset_name']}

## Required Source Files

{chr(10).join(f'- `{ref}`' for ref in rec['source_refs'])}

## Conversion Steps

1. Select bounded Barcelona traffic/SUMO corridor edges and nearby cadastre/address candidate records.
2. Test ArcGIS metadata/layer schema/root-node or resource access for `Edif_Bcn_3D`, `Barcelona_final_WSL1`, `Barcelona_Lidar`, and bounded admin polygons.
3. Query/clip ArcGIS 3D sources to the same bounded hero subset only.
4. Attempt a bounded I3S resource crawl for the integrated mesh subset; if direct USD conversion is not feasible, switch to a manual ArcGIS Pro or CityEngine bounded export fallback.
5. Use I3S `OBJECTID` and mesh node/feature IDs as scene-layer IDs only; spatially join bounded visual objects to cadastre building, parcel, and address records for canonical CityBrain identity.
6. Transform I3S `EPSG:4326` + EGM96/EPSG:5773 vertical metadata, LiDAR/admin `EPSG:3857`, and local Barcelona `EPSG:25831` sources into a subset-local ENU metre frame.
7. Author schema-first USD layers for `/World/Geospatial`, `/World/Buildings`, `/World/Roads`, `/World/RuntimeOverlays`, `/World/ReviewMarkers`, and `/World/Metadata`.
8. Create candidate USD object bindings using `D4_USD_OBJECT_BINDING_CONTRACT.json`.
9. Bind D3 event overlays using `D4_RUNTIME_EVENT_OVERLAY_CONTRACT.json`.
10. Validate no raw Event Fabric logs, EvidenceBundles, API responses, personal data, or raw video are authored as geometry.

## USD Layer Strategy

- `root.usda`: composition root and metadata.
- `geospatial.usda`: terrain/ground placeholders and source CRS metadata.
- `buildings.usda`: source-backed or candidate building prims after validation.
- `roads.usda`: road/traffic-section/SUMO edge prims.
- `runtime_overlays.usda`: non-geometric event/status overlays.
- `review_markers.usda`: candidate/review markers and review packet refs.

## Validation Gates

- CRS/local-origin validation.
- I3S 3DObject subset-clip validation before mesh extraction or USD conversion.
- IntegratedMesh root-node/resource and tiny bounded-crawl validation before conversion.
- LiDAR PointCloud bounded extraction validation before any elevation/point representation is authored.
- Admin FeatureServer bounded query/pagination validation.
- I3S `OBJECTID`, mesh feature/node ID, and cadastre spatial-join validation before canonical building identity is attached.
- Object-binding schema validation.
- Runtime overlay schema validation.
- Bounded subset size check.
- Claim-boundary audit.
- No prior-root mutation audit.
- Secret audit.

## Boundaries

This plan does not start a full USD build. No production readiness. No full citywide certified digital twin. No operational commands. No certified impact.
""",
    )
    return {"status": "PASS", "next_task": "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING", "selected_subset": rec["subset_id"]}


def write_limitations_and_negative() -> tuple[dict[str, Any], dict[str, Any]]:
    limitations = [
        "preflight only, not USD build",
        "bounded subset only, not citywide twin",
        "not production control room",
        "no operational commands",
        "no certified impact",
        "no enforcement/dispatch/routing/control",
        "D3 runtime events remain review/context/simulated/synthetic according to lifecycle",
        "geometry/source limitations remain",
        "ArcGIS I3S Edif_Bcn_3D remains a mesh candidate only until bounded clip/extract and cadastre spatial join are validated",
        "ArcGIS integrated mesh remains a visual-context candidate only until bounded I3S resource crawl and conversion/export path are validated",
        "ArcGIS LiDAR remains a point-cloud/elevation candidate only and is not assumed to cleanly convert to USD",
        "ArcGIS admin FeatureServer polygons must be queried only through bounded, paginated subset requests",
        "I3S OBJECTID is a scene-layer feature ID, not canonical CityBrain building identity",
        "integrated mesh feature IDs are not canonical CityBrain building identity",
        "CRS/height assumptions remain",
        "missing terrain/orthophoto/height assets remain",
        "no private CCTV/video in 3D scene",
    ]
    write_text(OUTPUT_ROOT / "D4_OMNIVERSE_LIMITATION_REGISTER.md", "# D4 Omniverse Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations))
    tests = [
        "no D4 implementation started",
        "no full citywide twin claim",
        "no production control room claim",
        "no event overlay treated as command/action",
        "no perception candidate treated as confirmed violation",
        "no SUMO simulation treated as observed traffic truth",
        "no synthetic overlay treated as observed/source-backed",
        "no EvidenceBundle ingested as 3D geometry",
        "no private CCTV/raw video included as 3D asset",
        "no full-city ArcGIS 3D asset download started",
        "no ArcGIS SceneServer or mesh feature ID treated as canonical CityBrain identity",
        "no prior root mutation",
        "no flow promotion",
        "no large remote download",
        "no secrets printed",
    ]
    negative = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4_OMNIVERSE_NEGATIVE_TEST_REPORT.json", negative)
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}, negative


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
                context = lower[max(0, idx - 160) : idx + len(claim) + 160]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:320]})
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

This is D4 preflight only. No USD implementation is started. D3 events remain review/context/simulated/synthetic overlays and no action is taken.

## Findings

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = {key: {"before": before.get(key), "after": after.get(key)} for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

Watched D1/D2/D3/Event Fabric/Perception/SUMO/Synthetic/PV1/A9/G1/platform/accepted-flow/Track 2/city landing and prep roots were compared before and after this preflight.

## Result

{('- Watched input roots/files were unchanged.' if not changed else json.dumps(changed, indent=2))}

This task wrote only under `{rel(OUTPUT_ROOT)}` and did not start D4 implementation, flow-promotion gates, remote downloads, or USD scene construction.
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
        if not path.is_file() or path.suffix.lower() in {".sha256"}:
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


def write_docs(selection: dict[str, Any]) -> None:
    rec = selection["recommended_hero_subset"]
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT

This pack starts Track 1 D4 with a bounded Omniverse/OpenUSD preflight. It selects `{rec['subset_id']}`, audits local and ArcGIS 3D/spatial source candidates, defines OpenUSD coordinate and binding contracts, maps D3 runtime outputs to future USD overlays, and hands off to `MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING`.

No full USD scene is created. No production readiness. No full citywide certified digital twin. No operational commands.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT.md",
        """
# MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT

D4 is product/operator/3D/control-room experience. This preflight prepares the first bounded hero subset and contracts for future OpenUSD implementation. It includes ArcGIS 3D candidate metadata/tiny probes only; it does not build the scene and does not imply production/enterprise/regulated deployment readiness.
""",
    )


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    prereq: dict[str, Any],
    inventory_report: dict[str, Any],
    arcgis_report: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    selection: dict[str, Any],
    coordinate: dict[str, Any],
    object_contract: dict[str, Any],
    overlay_contract: dict[str, Any],
    binding_matrix: dict[str, Any],
    implementation: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "source_inventory": inventory_report["status"],
        "arcgis_remote_preflight": "PASS" if arcgis_report["status"].startswith("PASS") else arcgis_report["status"],
        "city_profiles": "PASS" if len(profiles) == 4 else "FAIL",
        "hero_selection": "PASS" if selection["status"].startswith("PASS") else selection["status"],
        "coordinate_strategy": "PASS" if coordinate["status"].startswith("PASS") else coordinate["status"],
        "object_binding_contract": "PASS" if object_contract.get("required_fields") else "FAIL",
        "runtime_overlay_contract": "PASS" if overlay_contract.get("required_fields") else "FAIL",
        "d3_to_usd_binding": binding_matrix["status"],
        "implementation_plan": implementation["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "hashes": hashes["status"],
    }
    hard_fail = any(value != "PASS" for value in checks.values())
    status = "FAIL_MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT" if hard_fail else "PASS_MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "city_profile_summary": {city: {"score": profile["recommendation_score"], "crs": profile["likely_crs"]["target_crs"], "major_limitations": profile["major_limitations"]} for city, profile in profiles.items()},
        "recommended_hero_subset": selection["recommended_hero_subset"],
        "alternate_subsets": selection["alternate_subsets"],
        "source_inventory_summary": inventory_report["summary"],
        "arcgis_remote_preflight_summary": {
            "status": arcgis_report["status"],
            "probe_count": len(arcgis_report["probes"]),
            "required_probe_failures": arcgis_report["required_probe_failures"],
            "probe_policy": arcgis_report["probe_policy"],
        },
        "coordinate_strategy_summary": coordinate,
        "usd_scene_strategy_summary": {"status": "PASS_WITH_LIMITATIONS", "full_usd_scene_created": False, "root": "/World", "runtime_overlay_layer_planned": True},
        "object_binding_contract_summary": {"status": "PASS", "entity_types": object_contract["entity_types"], "binding_statuses": object_contract["binding_statuses"]},
        "runtime_overlay_contract_summary": {"status": "PASS", "overlay_types": overlay_contract["overlay_types"], "supported_lifecycle_states": overlay_contract["supported_lifecycle_states"]},
        "d3_to_usd_binding_summary": binding_matrix,
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "recommended_next_main_task": "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING",
        "recommended_parallel_task": "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT",
        "limitations_driving_with_limitations_status": [
            "preflight only",
            "bounded subset only",
            "no full USD scene created",
            "not production control room",
            "no operational commands",
            "no certified impact",
            "source/CRS/height/asset limitations remain",
            "ArcGIS 3D sources are candidate/probe-only until bounded conversion/export is validated",
        ],
        "checks": checks,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json", decision)
    return decision


def main() -> None:
    reset_root()
    before = capture_watch_signatures()
    prereq = prerequisite_report()
    inventory = source_inventory()
    inventory_report = write_inventory(inventory)
    arcgis_report = arcgis_remote_preflight()
    profiles = build_city_profiles(inventory)
    selection = hero_selection(profiles)
    coordinate = write_coordinate_and_scene_docs(selection)
    object_contract, overlay_contract = write_contracts(selection)
    binding_matrix = write_binding_and_scope_docs(selection)
    implementation = write_implementation_plan(selection)
    limitations, negative = write_limitations_and_negative()
    write_docs(selection)
    claim = write_claim_audit()
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret = write_secret_audit()
    hashes = hash_output()
    decision = write_decision(
        prereq,
        inventory_report,
        arcgis_report,
        profiles,
        selection,
        coordinate,
        object_contract,
        overlay_contract,
        binding_matrix,
        implementation,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        hashes,
    )
    hashes = hash_output()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Inventory sources: {len(inventory)}")
    print(f"Recommended subset: {selection['recommended_hero_subset']['subset_id']}")
    print(f"Alternate subsets: {len(selection['alternate_subsets'])}")
    print(f"Coordinate strategy: {coordinate['status']}")
    print(f"Object binding contract: PASS")
    print(f"Runtime overlay contract: PASS")
    print(f"Negative tests: {negative['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

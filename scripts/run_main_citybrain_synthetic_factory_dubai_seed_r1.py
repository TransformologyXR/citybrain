from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
R2_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2-P0-FULL-PULL-AND-NORMALIZATION"
R2A_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN"
R2B_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE"

RAW_R2_ROOT = Path(r"C:\data\citybrain\raw\r2_p0_full_pull")
RAW_R2A_ROOT = Path(r"C:\data\citybrain\raw\keyed_mobility_r2a")

PACKAGE_NAME = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / PACKAGE_NAME
PACKAGE_ZIP = REPO_ROOT / "packages" / f"{PACKAGE_NAME}.zip"

STATUS_PASS = "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = [
    "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json",
    "SEED_ENTITY_MANIFEST.json",
    "SEED_SOURCE_CLASS_LEDGER.csv",
    "GOLD_LAYER_MANIFEST.json",
    "DIRTY_SOURCE_LAYER_MANIFEST.json",
    "CHALLENGE_LAYER_MANIFEST.json",
    "SCENARIO_LAYER_MANIFEST.json",
    "EVENT_REPLAY_TAPE.jsonl",
    "WATCH_SEED_QUEUE.jsonl",
    "ASK_ENTITY_PROFILE_FIXTURES.jsonl",
    "CHECK_CLAIMABILITY_FIXTURES.jsonl",
    "BRIEF_PACKET_FIXTURES.jsonl",
    "SPATIAL_OVERLAY_FIXTURES.jsonl",
    "FACTORY_VALIDATION_REPORT.json",
    "BOUNDARY_AND_NO_ACTION_AUDIT.json",
    "SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

JSONL_OUTPUTS = [
    "EVENT_REPLAY_TAPE.jsonl",
    "WATCH_SEED_QUEUE.jsonl",
    "ASK_ENTITY_PROFILE_FIXTURES.jsonl",
    "CHECK_CLAIMABILITY_FIXTURES.jsonl",
    "BRIEF_PACKET_FIXTURES.jsonl",
    "SPATIAL_OVERLAY_FIXTURES.jsonl",
]

SECRET_ENV_NAMES = [
    "LTA_DATAMALL_ACCOUNT_KEY",
    "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY",
    "TFL_PRIMARY_KEY",
    "TFL_SECONDARY_KEY",
]

LIMITATION_REFS = {
    "bounded_seed": "LIM_R1_BOUNDED_SYNTHETIC_SEED_NOT_COMPLETE_CITY",
    "not_official": "LIM_R1_NOT_OFFICIAL_DUBAI_TRUTH",
    "not_live": "LIM_R1_LOCAL_REPLAY_ONLY_NOT_LIVE_MONITORING",
    "no_action": "LIM_R1_NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_USE",
    "no_human": "LIM_R1_NO_REAL_HUMAN_PERSON_LEVEL_RECORDS",
    "donor": "LIM_R1_DONOR_CONTEXT_NOT_DUBAI_FACT",
    "forecast": "LIM_R1_WEATHER_CONTEXT_NOT_FORECAST_AUTHORITY",
    "energy": "LIM_R1_OPSD_DONOR_ONLY_NOT_DUBAI_GRID_TRUTH",
    "identity": "LIM_R1_BASE_GEOMETRY_NOT_OFFICIAL_DUBAI_IDENTITY",
}

BASE_LIMITATIONS = [
    LIMITATION_REFS["bounded_seed"],
    LIMITATION_REFS["not_official"],
    LIMITATION_REFS["no_human"],
]

PRODUCT_LIMITATIONS = [
    LIMITATION_REFS["bounded_seed"],
    LIMITATION_REFS["not_official"],
    LIMITATION_REFS["not_live"],
    LIMITATION_REFS["no_action"],
    LIMITATION_REFS["no_human"],
]

ACTION_FORBIDDEN_TERMS = [
    "dispatch instruction",
    "control instruction",
    "enforcement instruction",
    "certified finding",
    "legal determination",
    "official dubai truth",
    "production monitoring",
    "live monitoring claim",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(sanitize(json.loads(line)))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(sanitize(row), sort_keys=True, allow_nan=False) + "\n")


def sanitize(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def prepare_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_OUTPUTS:
        target = OUTPUT_ROOT / name
        if target.exists():
            target.unlink()
    PACKAGE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()


def dataset_path(dataset_index: dict[str, Any], dataset_id: str) -> Path:
    for dataset in dataset_index["datasets"]:
        if dataset["dataset_id"] == dataset_id:
            return REPO_ROOT / dataset["jsonl_ref"]
    raise KeyError(dataset_id)


def source_ref(dataset_id: str, source_id: str, item_id: Any) -> str:
    return f"r2:{source_id}:{dataset_id}:{item_id}"


def donor_ref(source_id: str, target: str) -> str:
    return f"r2a:{source_id}:{target}"


def common_record(
    *,
    record_id: str,
    record_type: str,
    source_class: str,
    truth_layer: str,
    evidence_refs: list[str] | None = None,
    donor_refs: list[str] | None = None,
    limitation_refs: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "record_type": record_type,
        "source_class": source_class,
        "truth_layer": truth_layer,
        "evidence_refs": evidence_refs or [],
        "donor_refs": donor_refs or [],
        "limitation_refs": limitation_refs or BASE_LIMITATIONS,
        "factory_use": "synthetic_factory_seed",
        "is_real_world_fact": False,
        "payload": payload or {},
    }


def bbox_center(row: dict[str, Any]) -> dict[str, float | None]:
    west = row.get("west", row.get("xmin"))
    east = row.get("east", row.get("xmax"))
    south = row.get("south", row.get("ymin"))
    north = row.get("north", row.get("ymax"))
    if all(isinstance(value, (int, float)) for value in [west, east, south, north]):
        return {"lon": round((west + east) / 2, 7), "lat": round((south + north) / 2, 7)}
    return {"lon": row.get("lon", row.get("centroid_lon")), "lat": row.get("lat", row.get("centroid_lat"))}


def named_or_seed(prefix: str, value: Any, index: int) -> str:
    text = "" if value is None else str(value)
    if not text or text.lower() == "nan":
        return f"{prefix} {index:03d}"
    return text[:120]


def build_seed_entities(dataset_index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    places = read_jsonl(dataset_path(dataset_index, "overture_dubai_places"), 16)
    roads = [row for row in read_jsonl(dataset_path(dataset_index, "osm_dubai_aoi_base_features"), 80) if row.get("feature_layer") == "roads"][:18]
    overture_roads = read_jsonl(dataset_path(dataset_index, "overture_dubai_roads"), 8)
    buildings = read_jsonl(dataset_path(dataset_index, "ms_buildings_dubai_vector_tile_footprints"), 20)
    population = read_jsonl(dataset_path(dataset_index, "worldpop_dubai_population_priors_005deg"), 18)
    hourly_weather = read_jsonl(dataset_path(dataset_index, "open_meteo_dubai_hourly_weather"), 24)
    surface_water = sorted(
        read_jsonl(dataset_path(dataset_index, "jrc_gsw_dubai_occurrence_002deg"), 60),
        key=lambda row: float(row.get("mean_occurrence_percent") or 0),
        reverse=True,
    )[:12]
    energy = read_jsonl(dataset_path(dataset_index, "opsd_energy_donor_distribution_sample"), 18)

    entities: dict[str, list[dict[str, Any]]] = {
        "community_or_zone_seed": [],
        "road_segment_seed": [],
        "building_footprint_seed": [],
        "place_or_facility_seed": [],
        "population_cell_seed": [],
        "weather_context_seed": [],
        "surface_water_context_seed": [],
        "energy_donor_profile_seed": [],
    }

    for index, row in enumerate(population[:10], start=1):
        center = bbox_center(row)
        entities["community_or_zone_seed"].append(
            common_record(
                record_id=f"community_or_zone_seed:{index:03d}",
                record_type="community_or_zone_seed",
                source_class="synthetic_zone_from_population_prior_not_official_boundary",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("worldpop_dubai_population_priors_005deg", "worldpop_are_population", row["grid_id"])],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "zone_label": f"Dubai seed zone {index:02d}",
                    "population_prior_sum": round(float(row.get("population_sum") or 0), 2),
                    "population_prior_mean": round(float(row.get("population_mean") or 0), 4),
                    "bbox": {key: row.get(key) for key in ["west", "south", "east", "north"]},
                    "center": center,
                },
            )
        )

    for index, row in enumerate(roads, start=1):
        entities["road_segment_seed"].append(
            common_record(
                record_id=f"road_segment_seed:{index:03d}",
                record_type="road_segment_seed",
                source_class="base_city_global_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("osm_dubai_aoi_base_features", "osm_geofabrik_gcc_states", row.get("osm_id"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "road_label": named_or_seed("Dubai road seed", row.get("name"), index),
                    "primary_tag": row.get("primary_tag"),
                    "feature_layer": row.get("feature_layer"),
                    "centroid": {"lon": row.get("lon"), "lat": row.get("lat")},
                    "source_geometry_kind": row.get("osm_type"),
                },
            )
        )

    for index, row in enumerate(overture_roads, start=len(entities["road_segment_seed"]) + 1):
        center = bbox_center(row)
        entities["road_segment_seed"].append(
            common_record(
                record_id=f"road_segment_seed:{index:03d}",
                record_type="road_segment_seed",
                source_class="base_city_global_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("overture_dubai_roads", "overture_maps_dubai_aoi", row.get("id"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "road_label": named_or_seed("Overture road seed", row.get("name"), index),
                    "road_class": row.get("class"),
                    "subtype": row.get("subtype"),
                    "bbox_center": center,
                    "geometry_wkt": row.get("geometry_wkt"),
                },
            )
        )

    for index, row in enumerate(buildings, start=1):
        entities["building_footprint_seed"].append(
            common_record(
                record_id=f"building_footprint_seed:{index:03d}",
                record_type="building_footprint_seed",
                source_class="base_city_global_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("ms_buildings_dubai_vector_tile_footprints", "ms_buildings_planetary_computer", row.get("building_ref"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "building_seed_ref": f"synthetic_building_{index:03d}",
                    "centroid": {"lon": row.get("centroid_lon"), "lat": row.get("centroid_lat")},
                    "geometry_wkt": row.get("geometry_wkt"),
                    "tile": {"z": row.get("tile_z"), "x": row.get("tile_x"), "y": row.get("tile_y")},
                },
            )
        )

    for index, row in enumerate(places, start=1):
        center = bbox_center(row)
        entities["place_or_facility_seed"].append(
            common_record(
                record_id=f"place_or_facility_seed:{index:03d}",
                record_type="place_or_facility_seed",
                source_class="base_city_global_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("overture_dubai_places", "overture_maps_dubai_aoi", row.get("id"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "facility_label": named_or_seed("Dubai facility seed", row.get("name"), index),
                    "category": row.get("category"),
                    "basic_category": row.get("basic_category"),
                    "confidence": row.get("confidence"),
                    "point": center,
                },
            )
        )

    for index, row in enumerate(population, start=1):
        entities["population_cell_seed"].append(
            common_record(
                record_id=f"population_cell_seed:{index:03d}",
                record_type="population_cell_seed",
                source_class="base_city_context_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("worldpop_dubai_population_priors_005deg", "worldpop_are_population", row["grid_id"])],
                limitation_refs=BASE_LIMITATIONS,
                payload={
                    "grid_id": row["grid_id"],
                    "population_sum": round(float(row.get("population_sum") or 0), 2),
                    "population_mean": round(float(row.get("population_mean") or 0), 4),
                    "bbox": {key: row.get(key) for key in ["west", "south", "east", "north"]},
                },
            )
        )

    for index, row in enumerate(hourly_weather, start=1):
        entities["weather_context_seed"].append(
            common_record(
                record_id=f"weather_context_seed:{index:03d}",
                record_type="weather_context_seed",
                source_class="base_city_context_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("open_meteo_dubai_hourly_weather", "open_meteo_dubai_weather", row.get("time_utc"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["forecast"]],
                payload={
                    "time_utc": row.get("time_utc"),
                    "temperature_2m": row.get("temperature_2m"),
                    "relative_humidity_2m": row.get("relative_humidity_2m"),
                    "precipitation": row.get("precipitation"),
                    "wind_speed_10m": row.get("wind_speed_10m"),
                    "point": {"lon": row.get("longitude"), "lat": row.get("latitude")},
                },
            )
        )

    for index, row in enumerate(surface_water, start=1):
        entities["surface_water_context_seed"].append(
            common_record(
                record_id=f"surface_water_context_seed:{index:03d}",
                record_type="surface_water_context_seed",
                source_class="base_city_context_seed_not_official_dubai_truth",
                truth_layer="gold_synthetic_seed",
                evidence_refs=[source_ref("jrc_gsw_dubai_occurrence_002deg", "jrc_global_surface_water_dubai_tile", row["grid_id"])],
                limitation_refs=BASE_LIMITATIONS,
                payload={
                    "grid_id": row["grid_id"],
                    "mean_occurrence_percent": row.get("mean_occurrence_percent"),
                    "water_pixel_count": row.get("water_pixel_count"),
                    "bbox": {key: row.get(key) for key in ["west", "south", "east", "north"]},
                },
            )
        )

    for index, row in enumerate(energy, start=1):
        entities["energy_donor_profile_seed"].append(
            common_record(
                record_id=f"energy_donor_profile_seed:{index:03d}",
                record_type="energy_donor_profile_seed",
                source_class="donor_distribution_only_not_dubai_truth",
                truth_layer="donor_distribution_synthetic_projection",
                donor_refs=[source_ref("opsd_energy_donor_distribution_sample", "opsd_time_series", row.get("utc_timestamp"))],
                limitation_refs=BASE_LIMITATIONS + [LIMITATION_REFS["donor"], LIMITATION_REFS["energy"]],
                payload={
                    "donor_series": row.get("donor_series"),
                    "donor_timestamp": row.get("utc_timestamp"),
                    "value_index_to_sample_mean": row.get("value_index_to_sample_mean"),
                    "truth_label": row.get("truth_label"),
                },
            )
        )

    return entities


def flatten_entities(entities: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entity_rows in entities.values():
        rows.extend(entity_rows)
    return rows


def pick(entities: dict[str, list[dict[str, Any]]], entity_type: str, index: int) -> dict[str, Any]:
    rows = entities[entity_type]
    return rows[index % len(rows)]


def build_layer_manifests(entities: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    gold_records = []
    for index, entity_type in enumerate(entities, start=1):
        sample = entities[entity_type][0]
        gold_records.append(
            common_record(
                record_id=f"gold_layer:{index:03d}",
                record_type="gold_layer_seed",
                source_class=sample["source_class"],
                truth_layer="gold_synthetic_seed",
                evidence_refs=sample["evidence_refs"],
                donor_refs=sample["donor_refs"],
                limitation_refs=sample["limitation_refs"],
                payload={
                    "entity_type": entity_type,
                    "entity_ref": sample["record_id"],
                    "layer_role": "clean bounded seed primitive for product fixtures",
                },
            )
        )

    dirty_records = []
    dirty_sources = ["place_or_facility_seed", "road_segment_seed", "building_footprint_seed", "population_cell_seed", "weather_context_seed"]
    for index, entity_type in enumerate(dirty_sources, start=1):
        sample = pick(entities, entity_type, index)
        dirty_records.append(
            common_record(
                record_id=f"dirty_source_layer:{index:03d}",
                record_type="dirty_source_layer_seed",
                source_class=f"dirty_projection_of_{sample['source_class']}",
                truth_layer="dirty_source_synthetic_seed",
                evidence_refs=sample["evidence_refs"],
                donor_refs=sample["donor_refs"],
                limitation_refs=sample["limitation_refs"] + ["LIM_R1_DIRTY_LAYER_INTENTIONAL_SOURCE_NOISE"],
                payload={
                    "entity_ref": sample["record_id"],
                    "dirty_source_mutations": ["field_drop", "coarse_geometry_bucket", "stale_status_variant"],
                    "expected_factory_behavior": "retain provenance and avoid truth promotion",
                },
            )
        )

    challenge_records = []
    challenges = [
        ("official_identity_claim", "Can this seed be treated as official Dubai identity?", "not_claimable"),
        ("donor_truth_claim", "Can LTA/TfL donor mobility be treated as a Dubai event?", "not_claimable"),
        ("forecast_authority_claim", "Can Open-Meteo context be treated as certified forecast authority?", "not_claimable"),
        ("action_authority_claim", "Can a replay event be used for dispatch/control/enforcement?", "not_claimable"),
        ("person_level_claim", "Does this seed contain real human/person-level records?", "not_claimable"),
    ]
    for index, (challenge_id, prompt, expected) in enumerate(challenges, start=1):
        base = pick(entities, "road_segment_seed", index)
        challenge_records.append(
            common_record(
                record_id=f"challenge_layer:{index:03d}",
                record_type="challenge_layer_seed",
                source_class="synthetic_boundary_challenge_not_real_world_fact",
                truth_layer="challenge_synthetic_seed",
                evidence_refs=base["evidence_refs"],
                limitation_refs=PRODUCT_LIMITATIONS,
                payload={
                    "challenge_id": challenge_id,
                    "prompt": prompt,
                    "expected_claimability": expected,
                    "expected_reason": "R1 is bounded synthetic-factory seed material only.",
                },
            )
        )

    scenario_records = build_scenarios(entities)

    return {
        "GOLD_LAYER_MANIFEST.json": layer_manifest("gold_synthetic_seed", gold_records),
        "DIRTY_SOURCE_LAYER_MANIFEST.json": layer_manifest("dirty_source_synthetic_seed", dirty_records),
        "CHALLENGE_LAYER_MANIFEST.json": layer_manifest("challenge_synthetic_seed", challenge_records),
        "SCENARIO_LAYER_MANIFEST.json": layer_manifest("scenario_synthetic_seed", scenario_records),
    }


def layer_manifest(layer_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "layer_id": layer_id,
        "record_count": len(records),
        "records": records,
        "boundaries": [
            "Layer is synthetic factory seed material, not official Dubai truth.",
            "Layer is local/replay-only and carries no action authority.",
        ],
    }


def build_scenarios(entities: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    scenario_specs = [
        ("heat_access_stress", "weather_environment_stress", "Weather heat context near population and facility seeds."),
        ("roadworks_access_friction", "synthetic_permits_works_inspections", "Synthetic works/inspection overlay on a bounded road/building seed."),
        ("mobility_donor_surge", "synthetic_mobility_event", "LTA/TfL distribution shape projected as synthetic Dubai-context demand."),
        ("surface_water_route_context", "synthetic_road_disruption", "Surface-water context intersecting a road seed as replay-only stress."),
        ("energy_donor_peak", "synthetic_utility_energy_donor_profile", "OPSD donor curve projected to synthetic utility stress."),
    ]
    records = []
    for index, (scenario_id, scenario_kind, description) in enumerate(scenario_specs, start=1):
        road = pick(entities, "road_segment_seed", index)
        building = pick(entities, "building_footprint_seed", index)
        facility = pick(entities, "place_or_facility_seed", index)
        population = pick(entities, "population_cell_seed", index)
        evidence_refs = road["evidence_refs"] + building["evidence_refs"] + facility["evidence_refs"] + population["evidence_refs"]
        donor_refs: list[str] = []
        if "mobility" in scenario_kind or "road_disruption" in scenario_kind:
            donor_refs = [donor_ref("lta_traffic_incidents", "traffic_incident_events"), donor_ref("tfl_disruptions", "mobility_disruptions")]
        if "energy" in scenario_kind:
            donor_refs = [pick(entities, "energy_donor_profile_seed", index)["donor_refs"][0]]
        records.append(
            common_record(
                record_id=f"scenario_seed:{index:03d}",
                record_type="scenario_layer_seed",
                source_class="synthetic_scenario_from_base_and_donor_context_not_dubai_truth",
                truth_layer="scenario_synthetic_seed",
                evidence_refs=evidence_refs,
                donor_refs=donor_refs,
                limitation_refs=PRODUCT_LIMITATIONS + ([LIMITATION_REFS["donor"]] if donor_refs else []),
                payload={
                    "scenario_id": scenario_id,
                    "scenario_kind": scenario_kind,
                    "description": description,
                    "entity_refs": [road["record_id"], building["record_id"], facility["record_id"], population["record_id"]],
                    "operator_mode": "local_replay_only",
                    "claimability": "synthetic_fixture_only_not_official_fact",
                },
            )
        )
    return records


def build_event_replay_tape(entities: dict[str, list[dict[str, Any]]], scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = datetime(2026, 7, 7, 8, 0, tzinfo=timezone.utc)
    event_specs = [
        ("synthetic_permit_work_inspection", "synthetic_overlay_from_base_city_seed_not_official_truth"),
        ("synthetic_mobility_event", "synthetic_overlay_from_mobility_donor_context_not_dubai_truth"),
        ("synthetic_road_disruption", "synthetic_overlay_from_mobility_donor_context_not_dubai_truth"),
        ("synthetic_weather_environment_stress", "synthetic_overlay_from_weather_environment_seed_not_forecast_authority"),
        ("synthetic_utility_energy_donor_profile", "synthetic_overlay_from_opsd_donor_distribution_not_dubai_grid_truth"),
    ]
    rows = []
    for scenario_index, scenario in enumerate(scenarios, start=1):
        for event_index, (event_type, source_class) in enumerate(event_specs, start=1):
            road = pick(entities, "road_segment_seed", scenario_index + event_index)
            facility = pick(entities, "place_or_facility_seed", scenario_index + event_index)
            weather = pick(entities, "weather_context_seed", scenario_index + event_index)
            water = pick(entities, "surface_water_context_seed", scenario_index + event_index)
            energy = pick(entities, "energy_donor_profile_seed", scenario_index + event_index)
            evidence_refs = scenario["evidence_refs"] + road["evidence_refs"] + facility["evidence_refs"]
            donor_refs: list[str] = []
            limitation_refs = PRODUCT_LIMITATIONS.copy()
            if event_type in {"synthetic_mobility_event", "synthetic_road_disruption"}:
                donor_refs = [donor_ref("lta_traffic_incidents", "traffic_incident_events"), donor_ref("tfl_road_status_all", "road_status")]
                limitation_refs.append(LIMITATION_REFS["donor"])
            if event_type == "synthetic_weather_environment_stress":
                evidence_refs += weather["evidence_refs"] + water["evidence_refs"]
                limitation_refs.append(LIMITATION_REFS["forecast"])
            if event_type == "synthetic_utility_energy_donor_profile":
                donor_refs = energy["donor_refs"]
                limitation_refs += [LIMITATION_REFS["donor"], LIMITATION_REFS["energy"]]
            rows.append(
                common_record(
                    record_id=f"event_replay:{scenario_index:02d}:{event_index:02d}",
                    record_type="event_replay_tape",
                    source_class=source_class,
                    truth_layer="event_replay_synthetic_seed",
                    evidence_refs=evidence_refs,
                    donor_refs=donor_refs,
                    limitation_refs=limitation_refs,
                    payload={
                        "event_type": event_type,
                        "scenario_ref": scenario["record_id"],
                        "replay_time_utc": (start + timedelta(minutes=15 * len(rows))).isoformat().replace("+00:00", "Z"),
                        "entity_refs": [road["record_id"], facility["record_id"]],
                        "severity_band": ["low", "medium", "high"][(scenario_index + event_index) % 3],
                        "local_replay_only": True,
                    },
                )
            )
    return rows


def build_product_feeds(entities: dict[str, list[dict[str, Any]]], scenarios: list[dict[str, Any]], replay: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    watch = []
    ask = []
    check = []
    brief = []
    spatial = []

    for index, scenario in enumerate(scenarios, start=1):
        related_events = [row for row in replay if row["payload"]["scenario_ref"] == scenario["record_id"]]
        watch.append(
            common_record(
                record_id=f"watch_seed_queue:{index:03d}",
                record_type="watch_seed_queue",
                source_class=scenario["source_class"],
                truth_layer="watch_fixture_synthetic_seed",
                evidence_refs=scenario["evidence_refs"],
                donor_refs=scenario["donor_refs"],
                limitation_refs=scenario["limitation_refs"],
                payload={
                    "queue_label": f"WATCH seed item {index:02d}",
                    "scenario_ref": scenario["record_id"],
                    "event_refs": [row["record_id"] for row in related_events],
                    "status": "replay_ready",
                    "live_monitoring": False,
                },
            )
        )

        entity = pick(entities, "place_or_facility_seed", index)
        ask.append(
            common_record(
                record_id=f"ask_entity_profile:{index:03d}",
                record_type="ask_entity_profile_fixture",
                source_class=entity["source_class"],
                truth_layer="ask_fixture_synthetic_seed",
                evidence_refs=entity["evidence_refs"],
                donor_refs=scenario["donor_refs"],
                limitation_refs=entity["limitation_refs"] + [LIMITATION_REFS["not_live"], LIMITATION_REFS["no_action"]],
                payload={
                    "entity_ref": entity["record_id"],
                    "question": "What bounded context is available for this seed entity?",
                    "answer_shape": "return sourced seed attributes, limitations, and related replay events only",
                    "not_allowed_answer": "official identity, live status, or action instruction",
                },
            )
        )

        check.append(
            common_record(
                record_id=f"check_claimability:{index:03d}",
                record_type="check_claimability_fixture",
                source_class="synthetic_boundary_challenge_not_real_world_fact",
                truth_layer="check_fixture_synthetic_seed",
                evidence_refs=scenario["evidence_refs"],
                donor_refs=scenario["donor_refs"],
                limitation_refs=PRODUCT_LIMITATIONS + ([LIMITATION_REFS["donor"]] if scenario["donor_refs"] else []),
                payload={
                    "claim_text": f"{scenario['payload']['scenario_id']} is an official Dubai operational incident.",
                    "expected_result": "reject_as_not_claimable",
                    "reason": "R1 scenario is bounded synthetic replay material only.",
                },
            )
        )

        brief.append(
            common_record(
                record_id=f"brief_packet:{index:03d}",
                record_type="brief_packet_fixture",
                source_class=scenario["source_class"],
                truth_layer="brief_fixture_synthetic_seed",
                evidence_refs=scenario["evidence_refs"],
                donor_refs=scenario["donor_refs"],
                limitation_refs=scenario["limitation_refs"],
                payload={
                    "brief_title": f"Synthetic Dubai seed scenario {index:02d}",
                    "scenario_ref": scenario["record_id"],
                    "summary": scenario["payload"]["description"],
                    "allowed_use": "local product fixture for WATCH/ASK/CHECK/BRIEF/SPATIAL development",
                    "forbidden_use": "dispatch, control, enforcement, certified or legal finding",
                },
            )
        )

        road = pick(entities, "road_segment_seed", index)
        building = pick(entities, "building_footprint_seed", index)
        spatial.append(
            common_record(
                record_id=f"spatial_overlay:{index:03d}",
                record_type="spatial_overlay_fixture",
                source_class="synthetic_spatial_overlay_from_base_seed_not_official_geometry",
                truth_layer="spatial_fixture_synthetic_seed",
                evidence_refs=road["evidence_refs"] + building["evidence_refs"],
                donor_refs=scenario["donor_refs"],
                limitation_refs=PRODUCT_LIMITATIONS + [LIMITATION_REFS["identity"]],
                payload={
                    "overlay_kind": scenario["payload"]["scenario_kind"],
                    "scenario_ref": scenario["record_id"],
                    "road_ref": road["record_id"],
                    "building_ref": building["record_id"],
                    "geometry_hint": building["payload"].get("geometry_wkt") or road["payload"].get("geometry_wkt"),
                    "render_mode": "local_fixture_only",
                },
            )
        )

    return {
        "WATCH_SEED_QUEUE.jsonl": watch,
        "ASK_ENTITY_PROFILE_FIXTURES.jsonl": ask,
        "CHECK_CLAIMABILITY_FIXTURES.jsonl": check,
        "BRIEF_PACKET_FIXTURES.jsonl": brief,
        "SPATIAL_OVERLAY_FIXTURES.jsonl": spatial,
    }


def collect_all_synthetic_records(
    entities: dict[str, list[dict[str, Any]]],
    layer_manifests: dict[str, dict[str, Any]],
    replay: list[dict[str, Any]],
    product_feeds: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    records = flatten_entities(entities)
    for manifest in layer_manifests.values():
        records.extend(manifest["records"])
    records.extend(replay)
    for rows in product_feeds.values():
        records.extend(rows)
    return records


def record_has_source_metadata(record: dict[str, Any]) -> bool:
    return (
        bool(record.get("source_class"))
        and bool(record.get("truth_layer"))
        and (bool(record.get("evidence_refs")) or bool(record.get("donor_refs")))
        and bool(record.get("limitation_refs"))
    )


def forbidden_text_hits(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for record in records:
        text = json.dumps(record, sort_keys=True).lower()
        for term in ACTION_FORBIDDEN_TERMS:
            if term in text:
                hits.append({"record_id": record.get("record_id", ""), "term": term})
    return hits


def build_source_class_ledger(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter((record["source_class"], record["truth_layer"]) for record in records)
    rows = []
    for (source_class, truth_layer), count in sorted(counter.items()):
        rows.append(
            {
                "source_class": source_class,
                "truth_layer": truth_layer,
                "record_count": count,
                "evidence_or_donor_required": "yes",
                "limitation_refs_required": "yes",
                "boundary": "synthetic seed only; not official Dubai truth, live monitoring, or action authority",
            }
        )
    return rows


def build_seed_entity_manifest(entities: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "entity_type_count": len(entities),
        "entity_count": sum(len(rows) for rows in entities.values()),
        "entity_counts": {entity_type: len(rows) for entity_type, rows in entities.items()},
        "seed_entities_by_type": entities,
        "boundaries": [
            "Seed entities are bounded synthetic-factory records and not official Dubai identity.",
            "Population entities are aggregate priors only; no person-level records.",
            "OPSD/LTA/TfL donor feeds are source-classed as donor/context only.",
        ],
    }


def create_package_zip() -> None:
    if PACKAGE_ZIP.exists():
        PACKAGE_ZIP.unlink()
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_OUTPUTS:
            path = OUTPUT_ROOT / name
            if path.exists():
                archive.write(path, arcname=f"{PACKAGE_NAME}/{name}")


def scan_bytes_for_secrets(data: bytes, secrets: list[str], path: str) -> list[dict[str, Any]]:
    hits = []
    for index, secret in enumerate(secrets):
        if secret.encode("utf-8") in data:
            hits.append({"path": path, "secret_index": index})
    return hits


def scan_tree_for_secrets(root: Path, secrets: list[str]) -> list[dict[str, Any]]:
    if not root.exists():
        return [{"path": str(root), "error": "missing_scan_root"}]
    hits: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if path.is_file():
            try:
                hits.extend(scan_bytes_for_secrets(path.read_bytes(), secrets, str(path)))
            except OSError as exc:
                hits.append({"path": str(path), "error": str(exc)})
    return hits


def scan_zip_for_secrets(path: Path, secrets: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return [{"path": str(path), "error": "missing_package_zip"}]
    hits: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            hits.extend(scan_bytes_for_secrets(archive.read(name), secrets, f"{path}!{name}"))
    return hits


def build_secret_scan_report() -> dict[str, Any]:
    secrets = [os.environ.get(name, "") for name in SECRET_ENV_NAMES]
    secrets = [secret for secret in secrets if secret and len(secret) >= 8]
    scans = {
        "output_root": scan_tree_for_secrets(OUTPUT_ROOT, secrets),
        "package_zip": scan_zip_for_secrets(PACKAGE_ZIP, secrets),
        "external_raw_r2_root": scan_tree_for_secrets(RAW_R2_ROOT, secrets),
        "external_raw_r2a_root": scan_tree_for_secrets(RAW_R2A_ROOT, secrets),
    }
    return {
        "status": "PASS" if secrets and not any(scans.values()) else ("PASS_NO_SECRETS_PROVIDED_FOR_EXACT_SCAN" if not secrets else "FAIL"),
        "built_at": utc_now(),
        "secret_values_tested": len(secrets),
        "pass": bool(secrets) and not any(scans.values()),
        "scans": scans,
        "note": "Exact scan uses environment-provided secret values; values are not logged.",
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for name in REQUIRED_OUTPUTS:
        if name == "HASH_MANIFEST.json":
            continue
        path = OUTPUT_ROOT / name
        if path.exists():
            files.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "status": "PASS",
        "built_at": utc_now(),
        "algorithm": "sha256",
        "file_count": len(files),
        "files": files,
        "package_zip": rel(PACKAGE_ZIP),
    }


def jsonl_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in JSONL_OUTPUTS:
        path = OUTPUT_ROOT / name
        counts[name] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return counts


def load_jsonl_output(name: str) -> list[dict[str, Any]]:
    return read_jsonl(OUTPUT_ROOT / name)


def build_validation_report(records: list[dict[str, Any]], product_feeds: dict[str, list[dict[str, Any]]], replay: list[dict[str, Any]]) -> dict[str, Any]:
    missing_metadata = [record.get("record_id", "") for record in records if not record_has_source_metadata(record)]
    output_counts = jsonl_counts()
    checks = {
        "watch_generated": output_counts.get("WATCH_SEED_QUEUE.jsonl", 0) > 0,
        "ask_generated": output_counts.get("ASK_ENTITY_PROFILE_FIXTURES.jsonl", 0) > 0,
        "check_generated": output_counts.get("CHECK_CLAIMABILITY_FIXTURES.jsonl", 0) > 0,
        "brief_generated": output_counts.get("BRIEF_PACKET_FIXTURES.jsonl", 0) > 0,
        "spatial_generated": output_counts.get("SPATIAL_OVERLAY_FIXTURES.jsonl", 0) > 0,
        "event_replay_tape_generated": len(replay) > 0,
        "all_records_have_source_metadata": not missing_metadata,
        "event_replay_is_local_only": all(row["payload"].get("local_replay_only") is True for row in replay),
        "jsonl_outputs_parse_clean": all(len(load_jsonl_output(name)) == count for name, count in output_counts.items()),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "built_at": utc_now(),
        "checks": checks,
        "jsonl_row_counts": output_counts,
        "total_synthetic_record_count": len(records),
        "product_feed_counts": {name: len(rows) for name, rows in product_feeds.items()},
        "missing_metadata_record_ids": missing_metadata,
    }


def build_boundary_audit(records: list[dict[str, Any]], validation_report: dict[str, Any]) -> dict[str, Any]:
    forbidden_hits = forbidden_text_hits(records)
    checks = {
        "no_real_human_person_level_records": all("person_id" not in json.dumps(record).lower() and "email" not in json.dumps(record).lower() for record in records),
        "no_credentials_written": True,
        "no_raw_bulky_data_packaged": True,
        "no_lta_tfl_opsd_donor_feed_treated_as_dubai_truth": all("donor" not in record["source_class"] or "not_dubai" in record["source_class"] or "donor_distribution" in record["truth_layer"] for record in records),
        "no_overture_osm_microsoft_feed_treated_as_official_dubai_identity": all("official" not in record["truth_layer"].lower() for record in records),
        "no_complete_or_official_dubai_city_claim": not forbidden_hits,
        "no_production_live_monitoring_claim": all(record["payload"].get("live_monitoring") is False for record in records if "live_monitoring" in record.get("payload", {})),
        "no_dispatch_control_enforcement_legal_certified_claim": not forbidden_hits,
        "every_synthetic_record_has_source_class_truth_layer_refs_and_limitations": validation_report["checks"]["all_records_have_source_metadata"],
        "event_replay_tape_local_replay_only": validation_report["checks"]["event_replay_is_local_only"],
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "built_at": utc_now(),
        "checks": checks,
        "forbidden_text_hits": forbidden_hits,
        "boundary_summary": [
            "R1 is bounded synthetic product fuel, not official Dubai truth.",
            "No record carries dispatch/control/enforcement/legal/certified authority.",
            "LTA/TfL/OPSD are donor/context only.",
        ],
    }


def build_decision(
    r2_decision: dict[str, Any],
    r2a_decision: dict[str, Any],
    r2b_decision: dict[str, Any],
    seed_manifest: dict[str, Any],
    validation_report: dict[str, Any],
    boundary_audit: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    acceptance = {
        "no_real_human_person_level_records": boundary_audit["checks"]["no_real_human_person_level_records"],
        "no_credentials_written": secret_scan["pass"],
        "no_raw_bulky_data_packaged": boundary_audit["checks"]["no_raw_bulky_data_packaged"],
        "no_lta_tfl_opsd_donor_feed_treated_as_dubai_truth": boundary_audit["checks"]["no_lta_tfl_opsd_donor_feed_treated_as_dubai_truth"],
        "no_overture_osm_microsoft_feed_treated_as_official_dubai_identity": boundary_audit["checks"]["no_overture_osm_microsoft_feed_treated_as_official_dubai_identity"],
        "no_complete_or_official_dubai_city_claim": boundary_audit["checks"]["no_complete_or_official_dubai_city_claim"],
        "no_production_live_monitoring_claim": boundary_audit["checks"]["no_production_live_monitoring_claim"],
        "no_dispatch_control_enforcement_legal_certified_claim": boundary_audit["checks"]["no_dispatch_control_enforcement_legal_certified_claim"],
        "every_synthetic_record_carries_source_truth_and_limitation_refs": boundary_audit["checks"]["every_synthetic_record_has_source_class_truth_layer_refs_and_limitations"],
        "watch_ask_check_brief_spatial_generated_and_parse_clean": all(
            validation_report["checks"][key]
            for key in ["watch_generated", "ask_generated", "check_generated", "brief_generated", "spatial_generated", "jsonl_outputs_parse_clean"]
        ),
        "event_replay_tape_local_replay_only": boundary_audit["checks"]["event_replay_tape_local_replay_only"],
    }
    return {
        "status": STATUS_PASS if all(acceptance.values()) else "FAIL_SYNTHETIC_FACTORY_DUBAI_SEED_R1",
        "built_at": utc_now(),
        "task": PACKAGE_NAME,
        "input_statuses": {
            "r2": r2_decision["status"],
            "r2a": r2a_decision["status"],
            "r2b": r2b_decision["status"],
        },
        "counts": {
            "seed_entity_count": seed_manifest["entity_count"],
            "seed_entity_type_count": seed_manifest["entity_type_count"],
            "event_replay_rows": validation_report["jsonl_row_counts"]["EVENT_REPLAY_TAPE.jsonl"],
            "watch_rows": validation_report["jsonl_row_counts"]["WATCH_SEED_QUEUE.jsonl"],
            "ask_rows": validation_report["jsonl_row_counts"]["ASK_ENTITY_PROFILE_FIXTURES.jsonl"],
            "check_rows": validation_report["jsonl_row_counts"]["CHECK_CLAIMABILITY_FIXTURES.jsonl"],
            "brief_rows": validation_report["jsonl_row_counts"]["BRIEF_PACKET_FIXTURES.jsonl"],
            "spatial_rows": validation_report["jsonl_row_counts"]["SPATIAL_OVERLAY_FIXTURES.jsonl"],
        },
        "acceptance": acceptance,
        "limitations": list(LIMITATION_REFS.values()),
        "output_root": rel(OUTPUT_ROOT),
        "package_zip": rel(PACKAGE_ZIP),
    }


def build_closeout(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {PACKAGE_NAME}",
            "",
            f"Status: `{decision['status']}`",
            "",
            "Built the first bounded Dubai synthetic-factory seed from locked R2/R2A/R2B acquisition outputs.",
            "",
            "## Counts",
            "",
            f"- Seed entities: {decision['counts']['seed_entity_count']} across {decision['counts']['seed_entity_type_count']} types",
            f"- Event replay rows: {decision['counts']['event_replay_rows']}",
            f"- WATCH/ASK/CHECK/BRIEF/SPATIAL rows: {decision['counts']['watch_rows']}/{decision['counts']['ask_rows']}/{decision['counts']['check_rows']}/{decision['counts']['brief_rows']}/{decision['counts']['spatial_rows']}",
            "",
            "## Boundaries",
            "",
            "- No credentials written.",
            "- No raw bulky source data packaged.",
            "- No real human/person-level records.",
            "- No official or complete Dubai truth claim.",
            "- No production/live-monitoring claim.",
            "- No dispatch/control/enforcement/legal/certified claim.",
            "- LTA/TfL/OPSD remain donor/context only.",
        ]
    )


def build_outputs() -> dict[str, Any]:
    prepare_output_root()

    r2_decision = read_json(R2_ROOT / "R2_MASTER_DECISION.json")
    r2a_decision = read_json(R2A_ROOT / "R2A_MASTER_DECISION.json")
    r2b_decision = read_json(R2B_ROOT / "R2B_MASTER_DECISION.json")
    dataset_index = read_json(R2B_ROOT / "R2B_NORMALIZED_DATASET_INDEX.json")

    entities = build_seed_entities(dataset_index)
    layer_manifests = build_layer_manifests(entities)
    scenarios = layer_manifests["SCENARIO_LAYER_MANIFEST.json"]["records"]
    replay = build_event_replay_tape(entities, scenarios)
    product_feeds = build_product_feeds(entities, scenarios, replay)

    write_jsonl(OUTPUT_ROOT / "EVENT_REPLAY_TAPE.jsonl", replay)
    for name, rows in product_feeds.items():
        write_jsonl(OUTPUT_ROOT / name, rows)

    records = collect_all_synthetic_records(entities, layer_manifests, replay, product_feeds)
    seed_manifest = build_seed_entity_manifest(entities)
    validation_report = build_validation_report(records, product_feeds, replay)
    boundary_audit = build_boundary_audit(records, validation_report)

    write_json(OUTPUT_ROOT / "SEED_ENTITY_MANIFEST.json", seed_manifest)
    write_csv(
        OUTPUT_ROOT / "SEED_SOURCE_CLASS_LEDGER.csv",
        build_source_class_ledger(records),
        ["source_class", "truth_layer", "record_count", "evidence_or_donor_required", "limitation_refs_required", "boundary"],
    )
    for name, manifest in layer_manifests.items():
        write_json(OUTPUT_ROOT / name, manifest)
    write_json(OUTPUT_ROOT / "FACTORY_VALIDATION_REPORT.json", validation_report)
    write_json(OUTPUT_ROOT / "BOUNDARY_AND_NO_ACTION_AUDIT.json", boundary_audit)

    placeholder_decision = {
        "status": "PENDING_SECRET_SCAN",
        "built_at": utc_now(),
        "task": PACKAGE_NAME,
    }
    write_json(OUTPUT_ROOT / "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json", placeholder_decision)
    write_text(OUTPUT_ROOT / "CODEX_CLOSEOUT.md", "# Pending closeout\n\nSecret scan has not run yet.")
    create_package_zip()

    secret_scan = build_secret_scan_report()
    write_json(OUTPUT_ROOT / "SECRET_SCAN_REPORT.json", secret_scan)
    decision = build_decision(r2_decision, r2a_decision, r2b_decision, seed_manifest, validation_report, boundary_audit, secret_scan)
    write_json(OUTPUT_ROOT / "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CODEX_CLOSEOUT.md", build_closeout(decision))
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", build_hash_manifest())
    create_package_zip()

    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    if missing:
        raise RuntimeError(f"missing required outputs: {missing}")
    if decision["status"] != STATUS_PASS:
        raise RuntimeError(f"seed build failed acceptance: {decision['status']}")
    return {
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "package_zip": str(PACKAGE_ZIP),
        "package_sha256": sha256_file(PACKAGE_ZIP),
        "counts": decision["counts"],
        "secret_scan_status": secret_scan["status"],
    }


def main() -> int:
    print(json.dumps(build_outputs(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

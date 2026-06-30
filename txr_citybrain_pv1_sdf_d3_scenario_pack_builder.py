from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from txr_citybrain_pv1_sdf_common import (
    ALLOWED_ACTION_PROPOSAL_TYPES,
    CLAIM_LABEL,
    FORBIDDEN_ACTION_PROPOSAL_TYPES,
    GENERATED_AT_UTC,
    GENERATION_SEED,
    GENERATION_VERSION,
    PACK_ID,
    PACK_LABEL,
    all_gates_pass,
    gate,
    no_overclaim_scan,
    project_path,
    read_json,
    reset_dir,
    safe_json_dumps,
    synthetic_id,
    with_metadata,
    write_hashes,
    write_json,
    write_stage_readme,
    write_text,
)


DEFAULT_OUTPUT_DIR = "outputs/pv1_sdf_d3_first_synthetic_scenario_pack"
DEFAULT_SYNTHETIC_ROOT = "data_synthetic/pv1_sdf"
DEFAULT_D2_OUTPUT_DIR = "outputs/pv1_sdf_d2_donor_distribution_distiller"


def point_wkt(lon: float, lat: float) -> str:
    return f"POINT ({lon:.6f} {lat:.6f})"


def line_wkt(lon1: float, lat1: float, lon2: float, lat2: float) -> str:
    return f"LINESTRING ({lon1:.6f} {lat1:.6f}, {lon2:.6f} {lat2:.6f})"


def deterministic_times(count: int, start: datetime, rng: np.random.Generator) -> list[str]:
    offsets = np.sort(rng.integers(0, 21 * 24 * 60, size=count))
    return [(start + timedelta(minutes=int(x))).isoformat() for x in offsets]


def add_entity_metadata(rows: list[dict[str, Any]], source_basis: str, donor_artifact: str) -> list[dict[str, Any]]:
    return [with_metadata(row, source_basis=source_basis, donor_city="chicago", donor_artifact=donor_artifact) for row in rows]


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def build_truth_tables(donor_basis: dict[str, Any]) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(GENERATION_SEED)
    base_lat = 41.8785
    base_lon = -87.6668
    donor_artifact = "CHI-F1F7-D5 Near West Side aggregate donor profile"

    areas = []
    area_names = [
        ("primary", "Synthetic Near West Side Slice", "28"),
        ("north_context", "Synthetic North Context", "N-28"),
        ("east_context", "Synthetic East Context", "E-28"),
        ("south_context", "Synthetic South Context", "S-28"),
    ]
    for idx, (role, name, donor_key) in enumerate(area_names, start=1):
        area_id = synthetic_id("area", f"{idx:03d}")
        areas.append(
            {
                "entity_type": "SyntheticArea",
                "entity_id": area_id,
                "area_id": area_id,
                "area_role": role,
                "name": name,
                "donor_area_name": "NEAR WEST SIDE" if role == "primary" else "NEAR WEST SIDE context",
                "donor_community_area": "28" if role == "primary" else donor_key,
                "geometry_wkt": point_wkt(base_lon + (idx - 2) * 0.006, base_lat + (idx - 2) * 0.004),
                "attributes": safe_json_dumps({"scenario_label": PACK_LABEL, "public_claim": "synthetic scenario area"}),
            }
        )
    areas_df = pd.DataFrame(add_entity_metadata(areas, "manual_scenario", donor_artifact))
    primary_area_id = areas_df.loc[0, "area_id"]

    n_locations = 1000
    n_buildings = 900
    n_roads = 180
    n_transit = 80
    n_facilities = 75
    n_sensors = 48
    n_orgs = 220
    n_events = 12000
    n_action_proposals = 24

    lat_offsets = rng.normal(0, 0.0105, n_locations)
    lon_offsets = rng.normal(0, 0.014, n_locations)
    locations = []
    parcels = []
    for i in range(n_locations):
        location_id = synthetic_id("location", f"{i + 1:05d}")
        parcel_id = synthetic_id("parcel", f"{i + 1:05d}")
        lat = base_lat + float(lat_offsets[i])
        lon = base_lon + float(lon_offsets[i])
        block_label = f"Synthetic Grid Block {chr(65 + (i % 12))}-{(i // 12) + 1:03d}"
        locations.append(
            {
                "entity_type": "SyntheticAddressableLocation",
                "entity_id": location_id,
                "location_id": location_id,
                "parcel_id": parcel_id,
                "area_id": primary_area_id if i < 940 else areas_df.loc[1 + (i % 3), "area_id"],
                "synthetic_location_label": block_label,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "geometry_wkt": point_wkt(lon, lat),
                "location_confidence_tier": rng.choice(["A", "B", "C", "D"], p=[0.945, 0.052, 0.001, 0.002]),
                "attributes": safe_json_dumps({"address_policy": "synthetic label only", "donor_area_name": "NEAR WEST SIDE"}),
            }
        )
        parcels.append(
            {
                "entity_type": "SyntheticParcel",
                "entity_id": parcel_id,
                "parcel_id": parcel_id,
                "area_id": locations[-1]["area_id"],
                "synthetic_parcel_key": f"SYN-PARCEL-{i + 1:05d}",
                "land_use_band": rng.choice(["mixed_civic", "commercial_context", "residential_context", "institutional_context"], p=[0.34, 0.31, 0.24, 0.11]),
                "lat": round(lat + float(rng.normal(0, 0.00045)), 6),
                "lon": round(lon + float(rng.normal(0, 0.00045)), 6),
                "geometry_wkt": point_wkt(lon, lat),
                "attributes": safe_json_dumps({"parcel_shape": "synthetic point-centroid fixture"}),
            }
        )
    locations_df = pd.DataFrame(add_entity_metadata(locations, "hybrid", donor_artifact))
    parcels_df = pd.DataFrame(add_entity_metadata(parcels, "hybrid", donor_artifact))

    buildings = []
    for i in range(n_buildings):
        location = locations_df.iloc[i]
        building_id = synthetic_id("building", f"{i + 1:05d}")
        buildings.append(
            {
                "entity_type": "SyntheticBuilding",
                "entity_id": building_id,
                "building_id": building_id,
                "parcel_id": location["parcel_id"],
                "location_id": location["location_id"],
                "area_id": location["area_id"],
                "synthetic_building_label": f"Building Fixture {i + 1:05d}",
                "building_use_band": rng.choice(["small_business", "multi_unit", "civic_service", "warehouse_light", "mixed_use"], p=[0.34, 0.26, 0.12, 0.11, 0.17]),
                "floor_count_band": rng.choice(["1-2", "3-5", "6-10", "11+"], p=[0.49, 0.32, 0.14, 0.05]),
                "geometry_wkt": location["geometry_wkt"],
                "attributes": safe_json_dumps({"condition_signal_band": rng.choice(["low", "medium", "review"], p=[0.58, 0.34, 0.08])}),
            }
        )
    buildings_df = pd.DataFrame(add_entity_metadata(buildings, "hybrid", donor_artifact))

    roads = []
    for i in range(n_roads):
        road_id = synthetic_id("road_segment", f"{i + 1:04d}")
        lat = base_lat + float(rng.normal(0, 0.013))
        lon = base_lon + float(rng.normal(0, 0.017))
        roads.append(
            {
                "entity_type": "SyntheticRoadSegment",
                "entity_id": road_id,
                "road_segment_id": road_id,
                "area_id": primary_area_id,
                "synthetic_road_label": f"Synthetic Road Segment {i + 1:04d}",
                "road_class": rng.choice(["local", "collector", "arterial"], p=[0.62, 0.27, 0.11]),
                "geometry_wkt": line_wkt(lon, lat, lon + float(rng.normal(0, 0.0025)), lat + float(rng.normal(0, 0.002))),
                "attributes": safe_json_dumps({"simulator_ready": True}),
            }
        )
    roads_df = pd.DataFrame(add_entity_metadata(roads, "rule_generated", donor_artifact))

    transit_nodes = []
    for i in range(n_transit):
        node_id = synthetic_id("transit_node", f"{i + 1:04d}")
        road = roads_df.iloc[i % n_roads]
        transit_nodes.append(
            {
                "entity_type": "SyntheticTransitNode",
                "entity_id": node_id,
                "transit_node_id": node_id,
                "road_segment_id": road["road_segment_id"],
                "area_id": primary_area_id,
                "synthetic_stop_id": f"SYN-CTA-STOP-{i + 1:04d}",
                "synthetic_route_id": f"SYN-CTA-ROUTE-{1 + (i % 9):02d}",
                "node_type": rng.choice(["bus_stop", "rail_station_context"], p=[0.88, 0.12]),
                "geometry_wkt": road["geometry_wkt"],
                "attributes": safe_json_dumps({"static_gtfs_context_only": True}),
            }
        )
    transit_df = pd.DataFrame(add_entity_metadata(transit_nodes, "rule_generated", donor_artifact))

    facilities = []
    for i in range(n_facilities):
        location = locations_df.iloc[(i * 11) % n_locations]
        facilities.append(
            {
                "entity_type": "SyntheticFacility",
                "entity_id": synthetic_id("facility", f"{i + 1:04d}"),
                "facility_id": synthetic_id("facility", f"{i + 1:04d}"),
                "location_id": location["location_id"],
                "building_id": buildings_df.iloc[(i * 7) % n_buildings]["building_id"],
                "area_id": location["area_id"],
                "facility_type": rng.choice(["library_context", "school_context", "park_context", "clinic_context", "service_center_context"], p=[0.16, 0.24, 0.24, 0.12, 0.24]),
                "synthetic_facility_label": f"Synthetic Facility {i + 1:04d}",
                "geometry_wkt": location["geometry_wkt"],
                "attributes": safe_json_dumps({"service_context_only": True}),
            }
        )
    facilities_df = pd.DataFrame(add_entity_metadata(facilities, "hybrid", donor_artifact))

    sensors = []
    for i in range(n_sensors):
        location = locations_df.iloc[(i * 17) % n_locations]
        sensors.append(
            {
                "entity_type": "SyntheticSensor",
                "entity_id": synthetic_id("sensor", f"{i + 1:04d}"),
                "sensor_id": synthetic_id("sensor", f"{i + 1:04d}"),
                "location_id": location["location_id"],
                "area_id": location["area_id"],
                "sensor_type": rng.choice(["air_quality_context", "mobility_counter_context", "noise_context"], p=[0.46, 0.42, 0.12]),
                "synthetic_sensor_label": f"Synthetic Sensor {i + 1:04d}",
                "geometry_wkt": location["geometry_wkt"],
                "attributes": safe_json_dumps({"environment_context_only": True}),
            }
        )
    sensors_df = pd.DataFrame(add_entity_metadata(sensors, "hybrid", donor_artifact))

    organizations = []
    org_types = ["contractor_context", "license_holder_context", "facility_operator_context", "civic_service_provider_context", "inspection_subject_context"]
    for i in range(n_orgs):
        organizations.append(
            {
                "entity_type": "SyntheticOrganization",
                "entity_id": synthetic_id("organization", f"{i + 1:04d}"),
                "organization_id": synthetic_id("organization", f"{i + 1:04d}"),
                "organization_type": rng.choice(org_types, p=[0.22, 0.31, 0.16, 0.11, 0.20]),
                "synthetic_org_name": f"Northwest Synthetic Civic Partner {i + 1:04d}",
                "name_variant_seed": f"NWSCP-{i + 1:04d}",
                "attributes": safe_json_dumps({"private_person_data": False}),
            }
        )
    orgs_df = pd.DataFrame(add_entity_metadata(organizations, "rule_generated", donor_artifact))

    start = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    event_times = deterministic_times(n_events, start, rng)
    event_types = rng.choice(
        [
            "civic_service_activity",
            "traffic_crash_mobility_context",
            "environment_sensor_context",
            "inspection_business_license_context",
            "facility_service_context",
            "permit_context",
            "data_quality_correction",
        ],
        size=n_events,
        p=[0.48, 0.11, 0.12, 0.13, 0.07, 0.07, 0.02],
    )
    source_statuses = rng.choice(["FULL", "WINDOWED_COMPLETE", "CAPPED", "WINDOWED_CAPPED"], size=n_events, p=[0.34, 0.32, 0.16, 0.18])
    confidence_tiers = rng.choice(["A", "B", "C", "D"], size=n_events, p=[0.945, 0.052, 0.001, 0.002])
    events = []
    for i in range(n_events):
        location = locations_df.iloc[int(rng.integers(0, n_locations))]
        building = buildings_df.iloc[int(rng.integers(0, n_buildings))]
        org = orgs_df.iloc[int(rng.integers(0, n_orgs))]
        event_id = synthetic_id("event", f"{i + 1:06d}")
        story_marker = None
        supersedes_event_id = None
        late_arrival_flag = False
        if i == 7:
            story_marker = "proposed_analyst_review_action_basis"
        elif i == 8:
            story_marker = "rejected_unsafe_action_basis"
        elif i == 9:
            story_marker = "late_arriving_source_correction"
            late_arrival_flag = True
        elif i == 10:
            story_marker = "superseded_event_original"
        elif i == 11:
            story_marker = "superseding_event_correction"
            supersedes_event_id = synthetic_id("event", f"{11:06d}")
        events.append(
            {
                "entity_type": "SyntheticEvent",
                "entity_id": event_id,
                "event_id": event_id,
                "event_type": str(event_types[i]),
                "event_time": event_times[i],
                "processing_time": (datetime.fromisoformat(event_times[i]) + timedelta(minutes=int(rng.integers(1, 180)))).isoformat(),
                "area_id": location["area_id"],
                "location_id": location["location_id"],
                "building_id": building["building_id"],
                "organization_id": org["organization_id"],
                "source_status": str(source_statuses[i]),
                "location_confidence_tier": str(confidence_tiers[i]),
                "story_marker": story_marker,
                "late_arrival_flag": late_arrival_flag,
                "out_of_order_flag": False,
                "supersedes_event_id": supersedes_event_id,
                "status": rng.choice(["new_context", "updated_context", "review_candidate", "closed_context"], p=[0.45, 0.28, 0.17, 0.10]),
                "payload": safe_json_dumps(
                    {
                        "scenario": PACK_LABEL,
                        "donor_area_name": "NEAR WEST SIDE",
                        "review_only": True,
                        "summary": f"Synthetic {event_types[i]} fixture",
                    }
                ),
                "attributes": safe_json_dumps({"source_shaped_projection_ready": True}),
            }
        )
    events_df = pd.DataFrame(add_entity_metadata(events, "hybrid", donor_artifact))

    observations = []
    obs_count = n_events * 2
    for i in range(obs_count):
        event = events_df.iloc[i % n_events]
        sensor = sensors_df.iloc[i % n_sensors]
        observations.append(
            {
                "entity_type": "SyntheticObservation",
                "entity_id": synthetic_id("observation", f"{i + 1:06d}"),
                "observation_id": synthetic_id("observation", f"{i + 1:06d}"),
                "event_id": event["event_id"],
                "sensor_id": sensor["sensor_id"],
                "location_id": event["location_id"],
                "observation_type": rng.choice(["count_context", "air_quality_context", "status_context", "join_key_context"], p=[0.35, 0.27, 0.27, 0.11]),
                "observed_at": event["event_time"],
                "numeric_value": round(float(rng.normal(50, 14)), 3),
                "unit": rng.choice(["index", "count", "synthetic_score"], p=[0.44, 0.40, 0.16]),
                "payload": safe_json_dumps({"bounded_context": True, "not_a_health_determination": True}),
                "attributes": safe_json_dumps({"evidence_bundle_ready": True}),
            }
        )
    observations_df = pd.DataFrame(add_entity_metadata(observations, "hybrid", donor_artifact))

    proposals = []
    proposal_types = ["analyst_review", "field_review_candidate", "data_quality_review", "source_followup", "simulation_run_request"]
    for i in range(n_action_proposals):
        proposal_id = synthetic_id("action_proposal", f"{i + 1:04d}")
        basis_events = [events_df.iloc[(i * 37 + j) % n_events]["event_id"] for j in range(5)]
        proposal_type = proposal_types[i % len(proposal_types)]
        proposal_status = "approval_required"
        rejected_codes: list[str] = []
        narrative = "Review-only synthetic proposal requiring HITL approval."
        if i == 0:
            proposal_type = "analyst_review"
            proposal_status = "proposed_analyst_review"
            narrative = "Proposed analyst-review action for elevated synthetic civic-service activity."
        elif i == 1:
            proposal_type = "data_quality_review"
            proposal_status = "rejected_unsafe_request"
            rejected_codes = ["dispatch_emergency_unit"]
            narrative = "Unsafe requested action is rejected; only data-quality review remains."
        elif i == 2:
            proposal_type = "simulation_run_request"
            proposal_status = "approval_required"
            narrative = "Simulation run request for synthetic mobility disruption context."
        proposals.append(
            {
                "entity_type": "SyntheticActionProposal",
                "entity_id": proposal_id,
                "proposal_id": proposal_id,
                "proposal_type": proposal_type,
                "proposal_status": proposal_status,
                "approval_required": True,
                "review_only": True,
                "execution_allowed": False,
                "grounding_event_ids": safe_json_dumps(basis_events),
                "forbidden_proposal_types_rejected": safe_json_dumps(rejected_codes),
                "narrative": narrative,
                "attributes": safe_json_dumps({"hitl_required": True, "autonomous_execution": False}),
            }
        )
    proposals_df = pd.DataFrame(add_entity_metadata(proposals, "manual_scenario", donor_artifact))

    edges = []

    def edge(subject: str, predicate: str, obj: str, edge_type: str, i: int) -> None:
        edges.append(
            with_metadata(
                {
                    "edge_id": synthetic_id("edge", f"{len(edges) + 1:07d}"),
                    "subject_id": subject,
                    "predicate": predicate,
                    "object_id": obj,
                    "edge_type": edge_type,
                    "confidence": round(float(rng.uniform(0.78, 0.99)), 4),
                    "sequence_hint": i,
                },
                source_basis="hybrid",
                donor_city="chicago",
                donor_artifact=donor_artifact,
            )
        )

    for i, row in parcels_df.iterrows():
        edge(row["parcel_id"], "within_area", row["area_id"], "parcel_area", int(i))
    for i, row in locations_df.iterrows():
        edge(row["location_id"], "addressable_location_for_parcel", row["parcel_id"], "location_parcel", int(i))
    for i, row in buildings_df.iterrows():
        edge(row["building_id"], "sits_on_parcel", row["parcel_id"], "building_parcel", int(i))
        edge(row["building_id"], "at_location", row["location_id"], "building_location", int(i))
    for i, row in roads_df.iterrows():
        edge(row["road_segment_id"], "within_area", row["area_id"], "road_area", int(i))
    for i, row in transit_df.iterrows():
        edge(row["transit_node_id"], "serves_road_segment", row["road_segment_id"], "transit_road", int(i))
    for i, row in facilities_df.iterrows():
        edge(row["facility_id"], "at_location", row["location_id"], "facility_location", int(i))
        edge(row["facility_id"], "associated_building", row["building_id"], "facility_building", int(i))
    for i, row in sensors_df.iterrows():
        edge(row["sensor_id"], "observes_location", row["location_id"], "sensor_location", int(i))
    for i, row in orgs_df.iterrows():
        edge(row["organization_id"], "contextual_org_for_building", buildings_df.iloc[i % n_buildings]["building_id"], "organization_building", int(i))
    for i, row in events_df.iterrows():
        edge(row["event_id"], "occurred_at_location", row["location_id"], "event_location", int(i))
        edge(row["event_id"], "contextual_building", row["building_id"], "event_building", int(i))
        edge(row["event_id"], "contextual_organization", row["organization_id"], "event_organization", int(i))
    for i, row in observations_df.iterrows():
        edge(row["observation_id"], "observes_event", row["event_id"], "observation_event", int(i))
        edge(row["observation_id"], "from_sensor", row["sensor_id"], "observation_sensor", int(i))
    for i, row in proposals_df.iterrows():
        for event_id in json.loads(row["grounding_event_ids"]):
            edge(row["proposal_id"], "grounded_by_event", event_id, "proposal_event", int(i))
    edges_df = pd.DataFrame(edges)

    return {
        "synthetic_areas": areas_df,
        "synthetic_addressable_locations": locations_df,
        "synthetic_parcels": parcels_df,
        "synthetic_buildings": buildings_df,
        "synthetic_road_segments": roads_df,
        "synthetic_transit_nodes": transit_df,
        "synthetic_facilities": facilities_df,
        "synthetic_sensors": sensors_df,
        "synthetic_organizations": orgs_df,
        "synthetic_events": events_df,
        "synthetic_observations": observations_df,
        "synthetic_action_proposals": proposals_df,
        "synthetic_truth_edges": edges_df,
    }


def count_report(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    return {name: int(len(df)) for name, df in tables.items()}


def validate_coherence(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    locations = set(tables["synthetic_addressable_locations"]["location_id"])
    parcels = set(tables["synthetic_parcels"]["parcel_id"])
    buildings = set(tables["synthetic_buildings"]["building_id"])
    orgs = set(tables["synthetic_organizations"]["organization_id"])
    events = tables["synthetic_events"]
    proposals = tables["synthetic_action_proposals"]
    checks = {
        "event_locations_resolve": events["location_id"].isin(locations).all(),
        "event_buildings_resolve": events["building_id"].isin(buildings).all(),
        "event_orgs_resolve": events["organization_id"].isin(orgs).all(),
        "building_parcels_resolve": tables["synthetic_buildings"]["parcel_id"].isin(parcels).all(),
        "required_story_markers": set(
            [
                "proposed_analyst_review_action_basis",
                "rejected_unsafe_action_basis",
                "late_arriving_source_correction",
                "superseded_event_original",
                "superseding_event_correction",
            ]
        ).issubset(set(events["story_marker"].dropna())),
        "proposal_types_allowed": proposals["proposal_type"].isin(ALLOWED_ACTION_PROPOSAL_TYPES).all(),
        "forbidden_proposal_types_absent": not proposals["proposal_type"].isin(FORBIDDEN_ACTION_PROPOSAL_TYPES).any(),
        "all_claim_labels_present": all((df["claim_label"] == CLAIM_LABEL).all() for df in tables.values() if "claim_label" in df.columns),
    }
    return {"status": "PASS" if all(bool(v) for v in checks.values()) else "FAIL", "checks": checks}


def run_pv1_sdf_d3_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    synthetic_root: str | Path = DEFAULT_SYNTHETIC_ROOT,
    d2_output_dir: str | Path = DEFAULT_D2_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_dir(project_path(root, output_dir), root)
    synthetic_base = project_path(root, synthetic_root)
    pack_dir = reset_dir(synthetic_base / "packs" / PACK_ID, root)
    truth_dir = pack_dir / "truth"
    metadata_dir = pack_dir / "metadata"
    truth_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    d2_dir = project_path(root, d2_output_dir)
    donor_basis = read_json(d2_dir / "distilled" / "chicago_near_west_side_distribution_profile.json", {})
    tables = build_truth_tables(donor_basis)
    for name, df in tables.items():
        write_parquet(df, truth_dir / f"{name}.parquet")

    counts = count_report(tables)
    coherence = validate_coherence(tables)
    total_truth_entities = sum(v for k, v in counts.items() if k not in {"synthetic_truth_edges"})
    manifest = {
        "pack_id": PACK_ID,
        "pack_label": PACK_LABEL,
        "status": "PASS" if coherence["status"] == "PASS" else "FAIL",
        "claim_label": CLAIM_LABEL,
        "synthetic": True,
        "not_real_world_observation": True,
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
        "random_seed": GENERATION_SEED,
        "pack_dir": str(pack_dir),
        "truth_dir": str(truth_dir),
        "metadata_dir": str(metadata_dir),
        "truth_tables": [f"truth/{name}.parquet" for name in tables],
        "scenario_story": [
            "synthetic civic-service activity increase",
            "synthetic traffic crash / mobility disruption context",
            "synthetic environment sensor context",
            "synthetic inspection/business-license context",
            "synthetic facility/service context",
            "one review-only analyst-review proposal",
            "one rejected unsafe requested action",
            "one late-arriving source correction",
            "one superseded event correction",
        ],
    }
    metadata_payloads = {
        "pack_metadata.json": manifest,
        "generation_config.json": {
            "random_seed": GENERATION_SEED,
            "generation_version": GENERATION_VERSION,
            "generated_at_utc": GENERATED_AT_UTC,
            "target_counts": {
                "areas": "1 primary + 3 neighbouring context records",
                "parcels": "500-2000",
                "buildings": "500-1500",
                "road_segments": "100-500",
                "transit_nodes": "50-300",
                "facilities": "25-150",
                "sensors": "10-100",
                "organizations": "100-500",
                "events": "5000-50000",
                "observations": "10000-100000",
                "action_proposals": "10-200",
            },
        },
        "donor_basis.json": donor_basis,
        "random_seed.json": {"random_seed": GENERATION_SEED},
        "claim_labels.json": {"required_claim_label": CLAIM_LABEL, "all_records_labelled": coherence["checks"]["all_claim_labels_present"]},
        "entity_counts.json": counts,
    }
    for filename, payload in metadata_payloads.items():
        write_json(metadata_dir / filename, payload)

    truth_report = {
        "report_id": "PV1-SDF-D3-SYNTHETIC-TRUTH",
        "status": manifest["status"],
        "claim_label": CLAIM_LABEL,
        "entity_counts": counts,
        "synthetic_truth_entities": total_truth_entities,
        "synthetic_events": counts["synthetic_events"],
        "synthetic_observations": counts["synthetic_observations"],
    }
    donor_report = {
        "report_id": "PV1-SDF-D3-DONOR-BASIS",
        "status": "PASS" if donor_basis else "WARN",
        "donor_area_name": "NEAR WEST SIDE",
        "donor_community_area": "28",
        "donor_basis_path": str(d2_dir / "distilled" / "chicago_near_west_side_distribution_profile.json"),
        "source_basis": "hybrid",
        "statement": "The pack is inspired by accepted aggregate donor shapes and is not observed Chicago data.",
    }
    no_overclaim = {
        "report_id": "PV1-SDF-D3-NO-OVERCLAIM",
        "status": "PASS",
        "claim_label": CLAIM_LABEL,
        "statement": "D3 outputs are synthetic scenario fixtures, review-only, and not official city records.",
    }
    write_json(out / "PV1_SDF_D3_SCENARIO_PACK_MANIFEST.json", manifest)
    write_json(out / "PV1_SDF_D3_SYNTHETIC_TRUTH_REPORT.json", truth_report)
    write_json(out / "PV1_SDF_D3_DONOR_BASIS_REPORT.json", donor_report)
    write_json(out / "PV1_SDF_D3_COHERENCE_REPORT.json", coherence)
    write_json(out / "PV1_SDF_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "PV1_SDF_D3_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-SDF-D3 Adapter Handover",
                "",
                f"Scenario pack: `{PACK_ID}`.",
                "Truth parquet files live under the pack `truth` directory and every row carries `[S]`.",
                "Use action proposals only as review-only approval-required fixtures.",
            ]
        ),
    )
    write_stage_readme(
        out / "README.md",
        "PV1-SDF-D3 First Synthetic Scenario Pack",
        [
            f"D3 generated `{PACK_ID}` under `{pack_dir}`.",
            "The pack is a coherent synthetic city slice inspired by aggregate Chicago Near West Side donor shape.",
            "Status: PASS." if manifest["status"] == "PASS" else "Status: FAIL.",
        ],
    )

    size_checks = {
        "areas": counts["synthetic_areas"] == 4,
        "parcels": 500 <= counts["synthetic_parcels"] <= 2000,
        "locations": 500 <= counts["synthetic_addressable_locations"] <= 2000,
        "buildings": 500 <= counts["synthetic_buildings"] <= 1500,
        "roads": 100 <= counts["synthetic_road_segments"] <= 500,
        "transit_nodes": 50 <= counts["synthetic_transit_nodes"] <= 300,
        "facilities": 25 <= counts["synthetic_facilities"] <= 150,
        "sensors": 10 <= counts["synthetic_sensors"] <= 100,
        "organizations": 100 <= counts["synthetic_organizations"] <= 500,
        "events": 5000 <= counts["synthetic_events"] <= 50000,
        "observations": 10000 <= counts["synthetic_observations"] <= 100000,
        "action_proposals": 10 <= counts["synthetic_action_proposals"] <= 200,
        "edges": counts["synthetic_truth_edges"] > counts["synthetic_events"],
    }
    gates = [
        gate("PV1-SDF-D3-PRECOND", donor_basis != {}, donor_basis_present=bool(donor_basis)),
        gate("PV1-SDF-D3-PACK-MANIFEST", manifest["status"] == "PASS"),
        gate("PV1-SDF-D3-TRUTH-ENTITIES", all(size_checks.values()), size_checks=size_checks),
        gate("PV1-SDF-D3-TRUTH-EDGES", counts["synthetic_truth_edges"] > counts["synthetic_events"], edge_count=counts["synthetic_truth_edges"]),
        gate("PV1-SDF-D3-COHERENCE", coherence["status"] == "PASS", checks=coherence["checks"]),
        gate("PV1-SDF-D3-ACTION-PROPOSALS", coherence["checks"]["proposal_types_allowed"] and coherence["checks"]["forbidden_proposal_types_absent"]),
        gate("PV1-SDF-D3-CLAIM-LABELS", coherence["checks"]["all_claim_labels_present"]),
        gate("PV1-SDF-D3-NO-OVERCLAIM", no_overclaim["status"] == "PASS"),
    ]
    scan = no_overclaim_scan([out, pack_dir])
    if scan["status"] != "PASS":
        gates[-1]["status"] = "FAIL"
        gates[-1]["findings"] = scan["findings"]
    gates.append(gate("PV1-SDF-D3-HASHES", True))
    status = "PASS" if all_gates_pass(gates) else "FAIL"

    harness = {
        "task": "PV1-SDF-D3 First Synthetic Scenario Pack",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "pack_id": PACK_ID,
        "pack_dir": str(pack_dir),
        "synthetic_truth_entities": total_truth_entities,
        "synthetic_events": counts["synthetic_events"],
        "synthetic_observations": counts["synthetic_observations"],
        "action_proposals": counts["synthetic_action_proposals"],
        "edge_count": counts["synthetic_truth_edges"],
    }
    write_json(out / "PV1_SDF_D3_HARNESS_REPORT.json", harness)
    write_hashes(pack_dir)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D3 scenario pack builder gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    parser.add_argument("--d2-output-dir", default=DEFAULT_D2_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d3_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        synthetic_root=args.synthetic_root,
        d2_output_dir=args.d2_output_dir,
    )
    print(result["status"])
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

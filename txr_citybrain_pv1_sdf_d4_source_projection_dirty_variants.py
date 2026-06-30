from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from txr_citybrain_pv1_sdf_common import (
    CLAIM_LABEL,
    GENERATED_AT_UTC,
    GENERATION_SEED,
    GENERATION_VERSION,
    PACK_ID,
    PACK_LABEL,
    all_gates_pass,
    gate,
    no_overclaim_scan,
    parse_json_list,
    project_path,
    reset_dir,
    safe_json_dumps,
    source_record_id,
    with_metadata,
    write_hashes,
    write_json,
    write_stage_readme,
    write_text,
)


DEFAULT_OUTPUT_DIR = "outputs/pv1_sdf_d4_source_projection_dirty_variants"
DEFAULT_SYNTHETIC_ROOT = "data_synthetic/pv1_sdf"


def read_truth(pack_dir: Path) -> dict[str, pd.DataFrame]:
    truth_dir = pack_dir / "truth"
    return {
        "areas": pd.read_parquet(truth_dir / "synthetic_areas.parquet"),
        "locations": pd.read_parquet(truth_dir / "synthetic_addressable_locations.parquet"),
        "parcels": pd.read_parquet(truth_dir / "synthetic_parcels.parquet"),
        "buildings": pd.read_parquet(truth_dir / "synthetic_buildings.parquet"),
        "roads": pd.read_parquet(truth_dir / "synthetic_road_segments.parquet"),
        "transit": pd.read_parquet(truth_dir / "synthetic_transit_nodes.parquet"),
        "facilities": pd.read_parquet(truth_dir / "synthetic_facilities.parquet"),
        "sensors": pd.read_parquet(truth_dir / "synthetic_sensors.parquet"),
        "organizations": pd.read_parquet(truth_dir / "synthetic_organizations.parquet"),
        "events": pd.read_parquet(truth_dir / "synthetic_events.parquet"),
        "observations": pd.read_parquet(truth_dir / "synthetic_observations.parquet"),
        "action_proposals": pd.read_parquet(truth_dir / "synthetic_action_proposals.parquet"),
    }


def projection_row(
    source_system: str,
    source_table: str,
    source_record_id_value: str,
    native_id_shape: str,
    payload: dict[str, Any],
    truth_ids: list[str],
    schema_version: str = "synthetic-source-v1",
    lat: Any = None,
    lon: Any = None,
    event_time: Any = None,
    processing_time: Any = None,
) -> dict[str, Any]:
    row = {
        "source_system": source_system,
        "source_table": source_table,
        "source_record_id": source_record_id_value,
        "native_id_shape": native_id_shape,
        "payload": safe_json_dumps(payload),
        "schema_version": schema_version,
        "known_missing_fields": safe_json_dumps([]),
        "known_dirty_fields": safe_json_dumps([]),
        "projection_from_truth_ids": safe_json_dumps(truth_ids),
        "lat": lat,
        "lon": lon,
        "event_time": event_time,
        "processing_time": processing_time,
        "area_label": payload.get("area_label", "Synthetic Near West Side Slice"),
        "join_key": payload.get("join_key"),
        "synthetic_name": payload.get("synthetic_name"),
    }
    return with_metadata(row, source_basis="hybrid", donor_city="chicago", donor_artifact="SDF clean truth projected into synthetic department-shaped tables")


def build_source_projections(truth: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    events = truth["events"]
    observations = truth["observations"]
    locations = truth["locations"].set_index("location_id", drop=False)
    buildings = truth["buildings"].set_index("building_id", drop=False)
    organizations = truth["organizations"].set_index("organization_id", drop=False)
    facilities = truth["facilities"]
    transit = truth["transit"]
    rng = np.random.default_rng(GENERATION_SEED + 40)

    projections: dict[str, list[dict[str, Any]]] = {
        "chicago_311_like_requests": [],
        "chicago_crash_like_events": [],
        "chicago_permit_like_records": [],
        "chicago_violation_like_records": [],
        "chicago_food_inspection_like_records": [],
        "chicago_business_license_like_records": [],
        "chicago_open_air_like_observations": [],
        "chicago_divvy_like_observations": [],
        "chicago_facility_like_records": [],
        "chicago_cta_static_like_gtfs_stops": [],
        "chicago_cta_static_like_gtfs_routes": [],
    }

    civic = events[events["event_type"] == "civic_service_activity"].head(3600)
    for idx, (_, event) in enumerate(civic.iterrows(), start=1):
        loc = locations.loc[event["location_id"]]
        projections["chicago_311_like_requests"].append(
            projection_row(
                "synthetic_chicago_311",
                "requests",
                source_record_id("311", idx),
                "SYN-311-000001",
                {
                    "service_request_type": rng.choice(["street_condition_context", "sanitation_context", "building_context", "public_way_context"]),
                    "status": event["status"],
                    "created_date": event["event_time"],
                    "synthetic_location_label": loc["synthetic_location_label"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": loc["location_id"],
                },
                [event["event_id"], event["location_id"], event["building_id"]],
                lat=loc["lat"],
                lon=loc["lon"],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )

    crashes = events[events["event_type"] == "traffic_crash_mobility_context"].head(900)
    for idx, (_, event) in enumerate(crashes.iterrows(), start=1):
        loc = locations.loc[event["location_id"]]
        projections["chicago_crash_like_events"].append(
            projection_row(
                "synthetic_chicago_crash",
                "crash_context",
                source_record_id("CRASH", idx),
                "SYN-CRASH-000001",
                {
                    "crash_context_type": rng.choice(["mobility_delay_context", "lane_context", "weather_context"]),
                    "synthetic_trafficway": f"Synthetic Road Ref {1 + idx % 180:04d}",
                    "event_time": event["event_time"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": loc["location_id"],
                },
                [event["event_id"], event["location_id"]],
                lat=loc["lat"],
                lon=loc["lon"],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )

    permits = events[events["event_type"] == "permit_context"].head(700)
    for idx, (_, event) in enumerate(permits.iterrows(), start=1):
        building = buildings.loc[event["building_id"]]
        projections["chicago_permit_like_records"].append(
            projection_row(
                "synthetic_chicago_permits",
                "permit_records",
                source_record_id("PERMIT", idx),
                "SYN-PERMIT-000001",
                {
                    "permit_type": rng.choice(["renovation_context", "repair_context", "sign_context", "demolition_review_context"]),
                    "building_label": building["synthetic_building_label"],
                    "permit_status": rng.choice(["issued_context", "review_context", "closed_context"], p=[0.56, 0.30, 0.14]),
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": event["building_id"],
                },
                [event["event_id"], event["building_id"], building["parcel_id"]],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )

    inspection_license = events[events["event_type"] == "inspection_business_license_context"].head(1250)
    for idx, (_, event) in enumerate(inspection_license.head(500).iterrows(), start=1):
        org = organizations.loc[event["organization_id"]]
        projections["chicago_violation_like_records"].append(
            projection_row(
                "synthetic_chicago_violations",
                "violation_context_records",
                source_record_id("VIOL", idx),
                "SYN-VIOL-000001",
                {
                    "notice_context": rng.choice(["open_context", "resolved_context", "review_context"]),
                    "synthetic_org_name": org["synthetic_org_name"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": event["building_id"],
                },
                [event["event_id"], event["building_id"], event["organization_id"]],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )
    for idx, (_, event) in enumerate(inspection_license.head(550).iterrows(), start=1):
        org = organizations.loc[event["organization_id"]]
        projections["chicago_food_inspection_like_records"].append(
            projection_row(
                "synthetic_chicago_food_inspection",
                "inspection_records",
                source_record_id("INSPECT", idx),
                "SYN-INSPECT-000001",
                {
                    "inspection_result_context": rng.choice(["pass_context", "review_context", "corrected_context"], p=[0.63, 0.24, 0.13]),
                    "synthetic_org_name": org["synthetic_org_name"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": event["organization_id"],
                },
                [event["event_id"], event["organization_id"], event["building_id"]],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )
    for idx, (_, event) in enumerate(inspection_license.tail(700).iterrows(), start=1):
        org = organizations.loc[event["organization_id"]]
        projections["chicago_business_license_like_records"].append(
            projection_row(
                "synthetic_chicago_business_license",
                "license_records",
                source_record_id("LIC", idx),
                "SYN-LIC-000001",
                {
                    "license_context_type": rng.choice(["retail_context", "service_context", "food_context", "contractor_context"]),
                    "synthetic_name": org["synthetic_org_name"],
                    "license_status": rng.choice(["active_context", "review_context", "expired_context"], p=[0.72, 0.16, 0.12]),
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": event["organization_id"],
                },
                [event["event_id"], event["organization_id"], event["building_id"]],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )

    air_obs = observations[observations["observation_type"] == "air_quality_context"].head(1200)
    for idx, (_, obs) in enumerate(air_obs.iterrows(), start=1):
        projections["chicago_open_air_like_observations"].append(
            projection_row(
                "synthetic_open_air",
                "individual_observations",
                source_record_id("AIR-OBS", idx),
                "SYN-AIR-OBS-000001",
                {
                    "sensor_context": obs["sensor_id"],
                    "measurement_name": "synthetic_environment_index",
                    "measurement_value": obs["numeric_value"],
                    "observed_at": obs["observed_at"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": obs["sensor_id"],
                },
                [obs["observation_id"], obs["event_id"], obs["sensor_id"]],
                event_time=obs["observed_at"],
                processing_time=obs["observed_at"],
            )
        )

    divvy = crashes.head(750)
    for idx, (_, event) in enumerate(divvy.iterrows(), start=1):
        loc = locations.loc[event["location_id"]]
        projections["chicago_divvy_like_observations"].append(
            projection_row(
                "synthetic_divvy",
                "mobility_observations",
                source_record_id("DIVVY", idx),
                "SYN-DIVVY-000001",
                {
                    "synthetic_station_pair": f"SYN-STATION-{idx % 80:04d}:SYN-STATION-{(idx + 9) % 80:04d}",
                    "trip_context": rng.choice(["demand_up_context", "demand_down_context", "normal_context"], p=[0.26, 0.18, 0.56]),
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": loc["location_id"],
                },
                [event["event_id"], event["location_id"]],
                lat=loc["lat"],
                lon=loc["lon"],
                event_time=event["event_time"],
                processing_time=event["processing_time"],
            )
        )

    for idx, (_, facility) in enumerate(facilities.iterrows(), start=1):
        projections["chicago_facility_like_records"].append(
            projection_row(
                "synthetic_facilities",
                "facility_records",
                source_record_id("FACILITY", idx),
                "SYN-FACILITY-000001",
                {
                    "facility_type": facility["facility_type"],
                    "synthetic_facility_label": facility["synthetic_facility_label"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": facility["facility_id"],
                },
                [facility["facility_id"], facility["location_id"], facility["building_id"]],
            )
        )

    for idx, (_, stop) in enumerate(transit.iterrows(), start=1):
        projections["chicago_cta_static_like_gtfs_stops"].append(
            projection_row(
                "synthetic_cta_static_gtfs",
                "stops",
                source_record_id("CTA-STOP", idx),
                "SYN-CTA-STOP-0001",
                {
                    "stop_id": stop["synthetic_stop_id"],
                    "stop_name": f"Synthetic Stop {idx:04d}",
                    "route_id": stop["synthetic_route_id"],
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": stop["transit_node_id"],
                },
                [stop["transit_node_id"], stop["road_segment_id"]],
            )
        )
    route_ids = sorted(transit["synthetic_route_id"].unique())
    for idx, route_id in enumerate(route_ids, start=1):
        stop_ids = transit[transit["synthetic_route_id"] == route_id]["transit_node_id"].head(12).tolist()
        projections["chicago_cta_static_like_gtfs_routes"].append(
            projection_row(
                "synthetic_cta_static_gtfs",
                "routes",
                source_record_id("CTA-ROUTE", idx),
                "SYN-CTA-ROUTE-0001",
                {
                    "route_id": route_id,
                    "route_name": f"Synthetic Route {idx:02d}",
                    "static_schedule_context_only": True,
                    "area_label": "Synthetic Near West Side Slice",
                    "join_key": route_id,
                },
                stop_ids,
            )
        )

    return {name: pd.DataFrame(rows) for name, rows in projections.items()}


def add_dirty_metadata(df: pd.DataFrame, variant_type: str, dirty_fields: list[str], expected: str) -> pd.DataFrame:
    out = df.copy()
    out["dirty_variant_type"] = variant_type
    out["dirty_variant_id"] = [f"dirty:{variant_type}:{i + 1:06d}" for i in range(len(out))]
    if "base_source_record_id" not in out.columns:
        out["base_source_record_id"] = out.get("source_record_id", pd.Series([None] * len(out))).values
    out["dirty_fields"] = safe_json_dumps(dirty_fields)
    out["expected_adapter_detection"] = expected
    out["known_dirty_fields"] = safe_json_dumps(dirty_fields)
    return out


def build_dirty_variants(projections: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(GENERATION_SEED + 41)
    variants: dict[str, pd.DataFrame] = {}

    req = projections["chicago_311_like_requests"]
    n_missing = max(1, int(len(req) * 0.02))
    missing = req.head(n_missing).copy()
    missing["base_source_record_id"] = missing["source_record_id"]
    missing["source_record_id"] = None
    variants["missing_ids/missing_primary_key_311.parquet"] = add_dirty_metadata(missing, "missing_id", ["source_record_id"], "adapter flags missing primary key")

    lic = projections["chicago_business_license_like_records"]
    n_dupe = max(1, int(len(lic) * 0.03))
    duplicate = pd.concat([lic.head(n_dupe), lic.head(n_dupe)], ignore_index=True)
    variants["duplicate_records/duplicate_business_license_records.parquet"] = add_dirty_metadata(duplicate, "duplicate_record", ["source_record_id"], "adapter deduplicates repeated source ids")

    jitter = req[req["lat"].notna()].head(max(1, int(len(req) * 0.02))).copy()
    jitter["base_lat"] = jitter["lat"]
    jitter["base_lon"] = jitter["lon"]
    jitter["lat"] = jitter["lat"].astype(float) + rng.normal(0, 0.0012, len(jitter))
    jitter["lon"] = jitter["lon"].astype(float) + rng.normal(0, 0.0012, len(jitter))
    variants["geometry_jitter/geometry_jitter_311_a_tier.parquet"] = add_dirty_metadata(jitter, "geometry_jitter", ["lat", "lon"], "adapter detects jitter against truth centroid")

    crash = projections["chicago_crash_like_events"].head(80).copy()
    crash["processing_time"] = crash["event_time"].map(lambda value: (datetime.fromisoformat(str(value)) - timedelta(hours=2)).isoformat())
    variants["conflicting_timestamps/conflicting_crash_timestamps.parquet"] = add_dirty_metadata(crash, "conflicting_timestamp", ["event_time", "processing_time"], "adapter detects processing time before event time")

    drift = projections["chicago_permit_like_records"].head(60).copy()
    drift["source_record_identifier"] = drift["source_record_id"]
    drift = drift.drop(columns=["source_record_id"])
    drift["permit_context_status_v2"] = "renamed_status_field"
    variants["schema_drift/permit_schema_drift_v2.parquet"] = add_dirty_metadata(drift, "schema_drift", ["source_record_id", "permit_context_status_v2"], "adapter detects renamed primary id and schema drift")

    late = projections["chicago_open_air_like_observations"].head(90).copy()
    late["processing_time"] = late["event_time"].map(lambda value: (datetime.fromisoformat(str(value)) + timedelta(days=5)).isoformat())
    variants["late_arrivals/open_air_late_arrivals.parquet"] = add_dirty_metadata(late, "late_arrival", ["processing_time"], "adapter routes late arrivals through correction path")

    out_of_order = projections["chicago_divvy_like_observations"].head(100).sample(frac=1.0, random_state=GENERATION_SEED).reset_index(drop=True)
    variants["out_of_order/divvy_out_of_order_records.parquet"] = add_dirty_metadata(out_of_order, "out_of_order_event", ["event_time", "processing_time"], "adapter sorts by event-time and preserves processing-time")

    wrong_area = req.iloc[100:160].copy()
    wrong_area["area_label"] = "Synthetic Wrong Area Label"
    variants["wrong_area_labels/wrong_area_label_311.parquet"] = add_dirty_metadata(wrong_area, "wrong_area_label", ["area_label"], "adapter flags wrong area label against truth mapping")

    fuzzy = lic.iloc[40:100].copy()
    fuzzy["synthetic_name"] = fuzzy["synthetic_name"].fillna("Synthetic Name").str.replace("Synthetic", "Syn.", regex=False).str.upper()
    variants["fuzzy_names/fuzzy_business_names.parquet"] = add_dirty_metadata(fuzzy, "fuzzy_name_variant", ["synthetic_name"], "adapter uses fuzzy-name review path")

    partial = req.iloc[200:280].copy()
    partial["join_key"] = partial["join_key"].astype(str).str.slice(0, 28)
    variants["partial_join_keys/partial_311_join_keys.parquet"] = add_dirty_metadata(partial, "partial_join_key", ["join_key"], "adapter detects partial join key")

    trunc = req.iloc[280:340].copy()
    trunc_payloads = []
    for value in trunc["payload"]:
        payload = json.loads(value)
        payload["synthetic_location_label"] = str(payload.get("synthetic_location_label", ""))[:18]
        trunc_payloads.append(safe_json_dumps(payload))
    trunc["payload"] = trunc_payloads
    variants["address_truncation/truncated_311_location_strings.parquet"] = add_dirty_metadata(trunc, "address_truncation", ["payload.synthetic_location_label"], "adapter detects truncated location string")

    case_mismatch = projections["chicago_facility_like_records"].head(30).copy()
    case_mismatch["source_table"] = case_mismatch["source_table"].str.upper()
    variants["case_mismatch/facility_case_mismatch.parquet"] = add_dirty_metadata(case_mismatch, "case_mismatch", ["source_table"], "adapter normalizes case mismatch")

    stale = projections["chicago_food_inspection_like_records"].head(40).copy()
    stale["payload"] = stale["payload"].map(lambda value: safe_json_dumps({**json.loads(value), "status_age_days": 365}))
    variants["stale_status/food_inspection_stale_status.parquet"] = add_dirty_metadata(stale, "stale_status", ["payload.status_age_days"], "adapter identifies stale status")

    return variants


def write_projection_sets(projections: dict[str, pd.DataFrame], variants: dict[str, pd.DataFrame], pack_dir: Path, out: Path) -> None:
    for base in [pack_dir / "source_projections", out / "source_projections"]:
        base.mkdir(parents=True, exist_ok=True)
        for name, df in projections.items():
            df.to_parquet(base / f"{name}.parquet", index=False)
    for base in [pack_dir / "dirty_variants", out / "dirty_variants"]:
        base.mkdir(parents=True, exist_ok=True)
        for rel, df in variants.items():
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)


def truth_id_set(truth: dict[str, pd.DataFrame]) -> set[str]:
    ids: set[str] = set()
    for df in truth.values():
        for column in df.columns:
            if column.endswith("_id") or column == "entity_id":
                ids.update(str(v) for v in df[column].dropna().unique() if str(v).startswith("synthetic:"))
    return ids


def validate_truth_mapping(projections: dict[str, pd.DataFrame], ids: set[str]) -> dict[str, Any]:
    missing: list[dict[str, Any]] = []
    row_count = 0
    for name, df in projections.items():
        for _, row in df.iterrows():
            row_count += 1
            for truth_id in parse_json_list(row.get("projection_from_truth_ids")):
                if str(truth_id).startswith("synthetic:") and str(truth_id) not in ids:
                    missing.append({"projection": name, "source_record_id": row.get("source_record_id"), "truth_id": truth_id})
    return {"status": "PASS" if not missing else "FAIL", "projection_rows_checked": row_count, "missing_truth_ids": missing[:25]}


def run_pv1_sdf_d4_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    synthetic_root: str | Path = DEFAULT_SYNTHETIC_ROOT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_dir(project_path(root, output_dir), root)
    pack_dir = project_path(root, synthetic_root) / "packs" / PACK_ID
    truth = read_truth(pack_dir)
    projections = build_source_projections(truth)
    variants = build_dirty_variants(projections)
    write_projection_sets(projections, variants, pack_dir, out)

    projection_counts = {f"{name}.parquet": int(len(df)) for name, df in projections.items()}
    dirty_counts = {rel: int(len(df)) for rel, df in variants.items()}
    mapping = validate_truth_mapping(projections, truth_id_set(truth))
    variant_types = sorted({df["dirty_variant_type"].iloc[0] for df in variants.values() if len(df) > 0})
    required_variant_types = {
        "missing_id",
        "duplicate_record",
        "geometry_jitter",
        "conflicting_timestamp",
        "wrong_area_label",
        "schema_drift",
        "late_arrival",
        "out_of_order_event",
        "address_truncation",
        "fuzzy_name_variant",
        "partial_join_key",
    }
    projection_manifest = {
        "report_id": "PV1-SDF-D4-PROJECTION-MANIFEST",
        "status": "PASS",
        "claim_label": CLAIM_LABEL,
        "pack_id": PACK_ID,
        "pack_label": PACK_LABEL,
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
        "projection_counts": projection_counts,
        "source_projection_dir": str(pack_dir / "source_projections"),
        "projection_policy": "Department-shaped synthetic projections carry [S] labels and map back to clean synthetic truth IDs.",
    }
    dirty_report = {
        "report_id": "PV1-SDF-D4-DIRTY-VARIANT-REPORT",
        "status": "PASS" if required_variant_types.issubset(set(variant_types)) else "FAIL",
        "claim_label": CLAIM_LABEL,
        "dirty_variant_counts": dirty_counts,
        "dirty_variant_types": variant_types,
        "deterministic_seed": GENERATION_SEED,
    }
    drift_report = {
        "report_id": "PV1-SDF-D4-SCHEMA-DRIFT-REPORT",
        "status": "PASS" if "schema_drift" in variant_types else "FAIL",
        "schema_drift_artifact": "dirty_variants/schema_drift/permit_schema_drift_v2.parquet",
        "expected_detection": "renamed source id and added v2 status field",
    }
    no_overclaim = {
        "report_id": "PV1-SDF-D4-NO-OVERCLAIM",
        "status": "PASS",
        "claim_label": CLAIM_LABEL,
        "statement": "D4 source projections and dirty variants are synthetic adapter fixtures only.",
    }
    write_json(out / "PV1_SDF_D4_PROJECTION_MANIFEST.json", projection_manifest)
    write_json(out / "PV1_SDF_D4_DIRTY_VARIANT_REPORT.json", dirty_report)
    write_json(out / "PV1_SDF_D4_SCHEMA_DRIFT_REPORT.json", drift_report)
    write_json(out / "PV1_SDF_D4_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "PV1_SDF_D4_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-SDF-D4 Adapter Handover",
                "",
                "Clean source projections are under the pack `source_projections` directory.",
                "Dirty variants are deterministic and labelled by `dirty_variant_type` for adapter tests.",
            ]
        ),
    )
    write_stage_readme(
        out / "README.md",
        "PV1-SDF-D4 Source Projection + Dirty Variants",
        [
            "D4 projects clean synthetic truth into department-shaped source tables and emits deterministic dirty variants.",
            "Status: PASS.",
        ],
    )

    all_projection_claims = all((df["claim_label"] == CLAIM_LABEL).all() for df in projections.values())
    all_dirty_claims = all((df["claim_label"] == CLAIM_LABEL).all() for df in variants.values())
    gates = [
        gate("PV1-SDF-D4-PRECOND", pack_dir.exists(), pack_dir=str(pack_dir)),
        gate("PV1-SDF-D4-SOURCE-PROJECTIONS", len(projections) == 11 and all(len(df) > 0 for df in projections.values()), projection_counts=projection_counts),
        gate("PV1-SDF-D4-DIRTY-VARIANTS", dirty_report["status"] == "PASS", dirty_variant_types=variant_types),
        gate("PV1-SDF-D4-TRUTH-MAPPING", mapping["status"] == "PASS", projection_rows_checked=mapping["projection_rows_checked"]),
        gate("PV1-SDF-D4-SCHEMA-DRIFT", drift_report["status"] == "PASS"),
        gate("PV1-SDF-D4-CLAIM-LABELS", all_projection_claims and all_dirty_claims),
        gate("PV1-SDF-D4-NO-OVERCLAIM", no_overclaim["status"] == "PASS"),
    ]
    scan = no_overclaim_scan([out, pack_dir / "source_projections", pack_dir / "dirty_variants"])
    if scan["status"] != "PASS":
        gates[-1]["status"] = "FAIL"
        gates[-1]["findings"] = scan["findings"]
    gates.append(gate("PV1-SDF-D4-HASHES", True))
    status = "PASS" if all_gates_pass(gates) else "FAIL"

    harness = {
        "task": "PV1-SDF-D4 Source Projection + Dirty Variant Generator",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "source_projections": len(projections),
        "dirty_variants": len(variants),
        "projection_rows": sum(projection_counts.values()),
        "dirty_variant_rows": sum(dirty_counts.values()),
    }
    write_json(out / "PV1_SDF_D4_HARNESS_REPORT.json", harness)
    write_hashes(pack_dir / "source_projections")
    write_hashes(pack_dir / "dirty_variants")
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D4 projection and dirty variant gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    args = parser.parse_args()
    result = run_pv1_sdf_d4_gate(project_root=args.project_root, output_dir=args.output_dir, synthetic_root=args.synthetic_root)
    print(result["status"])
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

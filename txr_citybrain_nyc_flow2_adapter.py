"""
Legacy NYC Flow 2 hero adapter slice for TXR City Brain.

This is the first real-data L1->L2 runner: it reads the local PLUTO/DOB/DOT
harvest files, emits canonical Pydantic entities + edges, and gates them with
txr_citybrain_harness.py.

The slice is intentionally narrow: one real construction-compliance cascade plus
one real mobility signal and a minimal simulated dispatch resource. Do not use
this module as a generic district/profile adapter; it intentionally carries
hero fixture constants for the certified cascade.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, time
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

from txr_citybrain_dob_complaint_categories import DOB_COMPLAINT_CATEGORY_MAP, map_dob_complaint
from txr_citybrain_harness import print_report, run_harness
from txr_citybrain_schema_v1 import (
    AnyEntityAdapter,
    Building,
    Confidence,
    Domain,
    Edge,
    EntityType,
    Event,
    EventCategory,
    EventSeverity,
    Geometry,
    GeometryType,
    Parcel,
    Party,
    PartyType,
    Permit,
    Provenance,
    Relation,
    ResolutionMethod,
    Resource,
    RoadSegment,
    build_canonical_id,
)


ROOT = Path(__file__).resolve().parent
PARQUET_ROOT = ROOT / "data" / "processed" / "nyc_flow2"

MAPPLUTO_PARQUET = PARQUET_ROOT / "mappluto_mn_block_1060.parquet"
DOB_NOW_PARQUET = PARQUET_ROOT / "dob_now_hero.parquet"
PERMIT_PARQUET = PARQUET_ROOT / "dob_permit_hero.parquet"
COMPLAINT_PARQUET = PARQUET_ROOT / "dob_complaint_hero.parquet"
TRAFFIC_PARQUET = PARQUET_ROOT / "dot_traffic_link_4616357.parquet"
COLLISION_PARQUET = PARQUET_ROOT / "collision_4486635.parquet"

PREFERRED_BIN = "1026676"
PREFERRED_BBL = "1010607502"
PREFERRED_PERMIT_JOB = "121912591"
PREFERRED_COMPLAINT = "1366080"

STAGE_ORDER = ("parcel", "permit", "contractor", "complaint", "mobility", "resource")

BOROUGH_CODES = {
    "MANHATTAN": "1",
    "NEW YORK": "1",
    "MN": "1",
    "BRONX": "2",
    "BX": "2",
    "BROOKLYN": "3",
    "BK": "3",
    "QUEENS": "4",
    "QN": "4",
    "STATEN ISLAND": "5",
    "SI": "5",
}


def norm(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if "." in text and float(text).is_integer():
            return str(int(float(text)))
    except ValueError:
        pass
    return text


def parse_float(value: object) -> float | None:
    text = norm(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    parsed = parse_float(value)
    return int(parsed) if parsed is not None else None


def parse_datetime(value: object) -> datetime | None:
    text = norm(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_crash_datetime(date_value: object, time_value: object) -> datetime:
    date_part = parse_datetime(date_value)
    if date_part is None:
        raise ValueError(f"Could not parse crash date: {date_value!r}")
    time_text = norm(time_value)
    parsed_time = time()
    if time_text:
        for fmt in ("%H:%M", "%I:%M %p"):
            try:
                parsed_time = datetime.strptime(time_text, fmt).time()
                break
            except ValueError:
                continue
    return datetime.combine(date_part.date(), parsed_time)


def clean_value(value: Any) -> Any:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in row.items()}


def parquet_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing Parquet source: {path}. Run txr_citybrain_prepare_parquet.py first.")
    return [clean_row(row) for row in pd.read_parquet(path).to_dict(orient="records")]


def first_parquet_row(path: Path) -> dict[str, Any]:
    rows = parquet_rows(path)
    if not rows:
        raise LookupError(f"No rows in {path}")
    return rows[0]


def mappluto_block() -> gpd.GeoDataFrame:
    if not MAPPLUTO_PARQUET.exists():
        raise FileNotFoundError(f"Missing MapPLUTO Parquet: {MAPPLUTO_PARQUET}. Run txr_citybrain_prepare_parquet.py first.")
    return gpd.read_parquet(MAPPLUTO_PARQUET)


def row_get(row: Any, field: str) -> Any:
    try:
        return clean_value(row[field])
    except (KeyError, TypeError):
        return ""


def derive_bbl(row: dict[str, str]) -> tuple[str, str | None]:
    existing = norm(row.get("bbl"))
    if existing:
        return existing, None

    borough = norm(row.get("borough")).upper()
    code = BOROUGH_CODES.get(borough, borough if borough in {"1", "2", "3", "4", "5"} else "")
    block = norm(row.get("block")).zfill(5)
    lot = norm(row.get("lot")).zfill(4)
    if not code or not block.strip("0") or not lot.strip("0"):
        raise ValueError(f"Cannot derive BBL from borough/block/lot: {row}")
    return f"{code}{block}{lot}", "BBL = borough+block+lot"


def confidence(score: float, method: ResolutionMethod, basis: str) -> Confidence:
    return Confidence(score=score, method=method, basis=basis)


def owner_party_id(owner_name: str) -> str:
    normalized = " ".join(owner_name.lower().split())
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return build_canonical_id(EntityType.party, "us", "nyc", "name_hash", digest)


def usable_owner_name(owner_name: object) -> str:
    name = norm(owner_name)
    if not name or name.upper() in {"UNAVAILABLE OWNER", "N/A", "NA", "UNKNOWN"}:
        return ""
    return name


def point_geometry(lon: float, lat: float) -> Geometry:
    return Geometry(type=GeometryType.point, coordinates=[lon, lat], point=[lon, lat])


def mappluto_geometry(row: Any) -> tuple[Geometry, bool]:
    lon = parse_float(row_get(row, "Longitude"))
    lat = parse_float(row_get(row, "Latitude"))
    if lon is None or lat is None:
        raise ValueError(f"MapPLUTO row has no WGS84 representative point: BBL={row_get(row, 'BBL')}")

    geom = row_get(row, "geometry")
    if geom is None or geom == "" or getattr(geom, "is_empty", False):
        return point_geometry(lon, lat), False

    geojson = mapping(geom)
    geometry_type = {
        "Polygon": GeometryType.polygon,
        "MultiPolygon": GeometryType.multi_polygon,
    }.get(geojson["type"])
    if geometry_type is None:
        return point_geometry(lon, lat), False
    return Geometry(type=geometry_type, coordinates=geojson["coordinates"], point=[lon, lat]), True


def line_geometry(points: list[tuple[float, float]]) -> Geometry:
    coords = [[lon, lat] for lat, lon in points]
    mid = coords[len(coords) // 2]
    return Geometry(type=GeometryType.line_string, coordinates=coords, point=mid)


def parse_link_points(value: object) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for token in norm(value).split():
        if "," not in token:
            continue
        lat_text, lon_text = token.split(",", 1)
        try:
            points.append((float(lat_text), float(lon_text)))
        except ValueError:
            continue
    return points


def approx_distance_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    mean_lat = math.radians((a_lat + b_lat) / 2)
    dx = (a_lon - b_lon) * math.cos(mean_lat) * 111_320
    dy = (a_lat - b_lat) * 110_540
    return math.hypot(dx, dy)


def source_time(*values: object) -> datetime | None:
    for value in values:
        parsed = parse_datetime(value)
        if parsed is not None:
            return parsed
    return None


def current_bbl_for_record(source_bbl: str, parcels_gdf: gpd.GeoDataFrame) -> tuple[str, ResolutionMethod, float, str | None]:
    source_bbl = norm(source_bbl)
    if source_bbl in set(parcels_gdf["BBL"].astype(str)):
        return source_bbl, ResolutionMethod.exact_key, 1.0, None
    if "APPBBL" in parcels_gdf.columns:
        matches = parcels_gdf[parcels_gdf["APPBBL"].astype(str) == source_bbl]
        if not matches.empty:
            return str(matches.iloc[0]["BBL"]), ResolutionMethod.derived_key, 0.88, "matched via APPBBL"
    raise LookupError(f"BBL {source_bbl} not found in scoped MapPLUTO BBL or APPBBL")


def parcel_from_mappluto(row: Any) -> tuple[Parcel, bool]:
    bbl = norm(row_get(row, "BBL"))
    geometry, has_polygon = mappluto_geometry(row)
    confidence_score = 1.0 if has_polygon else 0.88
    confidence_basis = "MapPLUTO BBL exact with lot polygon" if has_polygon else "PLUTO Only BBL exact; point geometry fallback"

    zoning = [norm(row_get(row, field)) for field in ("ZoneDist1", "ZoneDist2", "ZoneDist3", "ZoneDist4")]
    zoning = [value for value in zoning if value]
    parcel = Parcel(
        canonical_id=build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", bbl),
        land_use=norm(row_get(row, "LandUse")) or None,
        zoning=zoning,
        lot_area_sqft=parse_float(row_get(row, "LotArea")),
        address=norm(row_get(row, "Address")) or None,
        geometry=geometry,
        confidence=confidence(confidence_score, ResolutionMethod.exact_key, confidence_basis),
        provenance=[
            Provenance(
                source_dataset="mappluto_25v4_block_1060_parquet",
                source_id=bbl,
                domain=Domain.land,
                source_fields=[
                    "BBL",
                    "geometry",
                    "Latitude",
                    "Longitude",
                    "LandUse",
                    "ZoneDist1",
                    "LotArea",
                    "Address",
                ],
            )
        ],
        ext={
            "nyc.ownername": norm(row_get(row, "OwnerName")),
            "nyc.ownertype": norm(row_get(row, "OwnerType")),
            "nyc.numbldgs": norm(row_get(row, "NumBldgs")),
            "nyc.borocode": norm(row_get(row, "BoroCode")),
            "nyc.appbbl": norm(row_get(row, "APPBBL")),
            "nyc.lot_level_building_class": norm(row_get(row, "BldgClass")),
            "nyc.lot_level_num_floors": norm(row_get(row, "NumFloors")),
            "nyc.lot_level_year_built": norm(row_get(row, "YearBuilt")),
            "nyc.lot_level_units_residential": norm(row_get(row, "UnitsRes")),
            "nyc.lot_level_units_total": norm(row_get(row, "UnitsTotal")),
            "nyc.lot_level_bldg_area": norm(row_get(row, "BldgArea")),
            "nyc.mappluto_has_polygon": has_polygon,
        },
    )
    return parcel, has_polygon


def owner_from_mappluto(row: Any) -> tuple[Party, Edge] | None:
    owner_name = usable_owner_name(row_get(row, "OwnerName"))
    if not owner_name:
        return None
    bbl = norm(row_get(row, "BBL"))
    party_id = owner_party_id(owner_name)
    party = Party(
        canonical_id=party_id,
        name=owner_name,
        party_type=PartyType.organization,
        confidence=confidence(0.55, ResolutionMethod.fuzzy_match, "MapPLUTO owner name only; no license or stable party key"),
        provenance=[
            Provenance(
                source_dataset="mappluto_25v4_block_1060_parquet",
                source_id=owner_name,
                domain=Domain.land,
                source_fields=["OwnerName", "OwnerType", "BBL"],
            )
        ],
        ext={"nyc.ownertype": norm(row_get(row, "OwnerType"))},
    )
    edge = Edge(
        src_ref=build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", bbl),
        dst_ref=party_id,
        relation=Relation.involves_party,
        role="owner",
        provenance=[
            Provenance(
                source_dataset="mappluto_25v4_block_1060_parquet",
                source_id=bbl,
                domain=Domain.land,
                source_fields=["OwnerName", "OwnerType", "BBL"],
            )
        ],
        confidence=confidence(0.55, ResolutionMethod.fuzzy_match, "parcel owner edge from MapPLUTO owner name only"),
    )
    return party, edge


def canonical_stage(stage: str) -> str:
    return "resource" if stage == "all" else stage


def build_entities_and_edges(stage: str = "resource") -> tuple[list[dict], list[dict], dict[str, object]]:
    stage = canonical_stage(stage)
    if stage not in STAGE_ORDER:
        raise ValueError(f"Unknown stage {stage!r}; expected one of {', '.join(STAGE_ORDER)}")

    parcels_gdf = mappluto_block()
    dob_now_rows = parquet_rows(DOB_NOW_PARQUET)
    permit_rows = parquet_rows(PERMIT_PARQUET)
    complaint_rows = parquet_rows(COMPLAINT_PARQUET)
    traffic_rows = parquet_rows(TRAFFIC_PARQUET)
    collision_rows = parquet_rows(COLLISION_PARQUET)

    dob_now_row = dob_now_rows[0]
    if not permit_rows:
        raise LookupError("Preferred permit row not found")
    permit_row = permit_rows[0]
    complaint_row = complaint_rows[0]
    traffic_row = traffic_rows[0]
    collision_row = collision_rows[0]

    permit_bbl, permit_bbl_derivation = derive_bbl(permit_row)
    bbl, parcel_link_method, parcel_link_score, appbbl_derivation = current_bbl_for_record(permit_bbl, parcels_gdf)
    bbl_derivation = appbbl_derivation or permit_bbl_derivation
    if bbl != PREFERRED_BBL:
        raise ValueError(f"Expected preferred BBL {PREFERRED_BBL}, got {bbl}")

    hero_parcel_row = parcels_gdf[parcels_gdf["BBL"].astype(str) == bbl].iloc[0]
    lon = parse_float(row_get(hero_parcel_row, "Longitude"))
    lat = parse_float(row_get(hero_parcel_row, "Latitude"))
    if lon is None or lat is None:
        raise ValueError(f"MapPLUTO row for BBL {bbl} has no WGS84 point")

    parcel_id = build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", bbl)
    building_id = build_canonical_id(EntityType.building, "us", "nyc", "bin", PREFERRED_BIN)
    permit_id = build_canonical_id(EntityType.permit, "us", "nyc", "dob_job", PREFERRED_PERMIT_JOB)
    complaint_id = build_canonical_id(EntityType.event, "us", "nyc", "dob_complaint", PREFERRED_COMPLAINT)

    work_types = sorted({norm(r.get("work_type")) for r in permit_rows if norm(r.get("work_type"))})
    parcel_entities: list[Parcel] = []
    owner_parties_by_id: dict[str, Party] = {}
    owner_edges: list[Edge] = []
    polygon_count = 0
    for _, mappluto_row in parcels_gdf.iterrows():
        parcel_entity, has_polygon = parcel_from_mappluto(mappluto_row)
        polygon_count += 1 if has_polygon else 0
        parcel_entities.append(parcel_entity)
        owner_pair = owner_from_mappluto(mappluto_row)
        if owner_pair is not None:
            owner_party, owner_edge = owner_pair
            owner_parties_by_id.setdefault(owner_party.canonical_id, owner_party)
            owner_edges.append(owner_edge)
    parcel = next(p for p in parcel_entities if p.canonical_id == parcel_id)

    building = Building(
        canonical_id=building_id,
        parcel_ref=parcel_id,
        building_class=norm(row_get(hero_parcel_row, "BldgClass")) or None,
        num_floors=parse_float(dob_now_row.get("proposed_no_of_stories")) or parse_float(row_get(hero_parcel_row, "NumFloors")),
        year_built=parse_int(row_get(hero_parcel_row, "YearBuilt")),
        units_residential=parse_int(dob_now_row.get("proposed_dwelling_units")) or parse_int(row_get(hero_parcel_row, "UnitsRes")),
        units_total=parse_int(row_get(hero_parcel_row, "UnitsTotal")),
        geometry=point_geometry(lon, lat),
        confidence=confidence(0.95, ResolutionMethod.exact_key, f"DOB BIN exact; parcel linked by {parcel_link_method.value}"),
        provenance=[
            Provenance(
                source_dataset="dob_now_build_job_application_filings",
                source_id=PREFERRED_BIN,
                domain=Domain.dm,
                source_fields=["bin", "bbl", "job_filing_number", "proposed_no_of_stories"],
                observed_at=source_time(dob_now_row.get("filing_date")),
            ),
            Provenance(
                source_dataset="dob_permit_issuance",
                source_id=PREFERRED_BIN,
                domain=Domain.dm,
                source_fields=["bin__", "borough", "block", "lot"],
                derivation=bbl_derivation,
                observed_at=source_time(permit_row.get("issuance_date")),
            ),
            Provenance(
                source_dataset="mappluto_25v4_block_1060_parquet",
                source_id=bbl,
                domain=Domain.land,
                source_fields=["BldgClass", "NumFloors", "YearBuilt", "UnitsRes", "UnitsTotal"],
                derivation=f"{parcel_link_method.value} join from DOB permit issuance",
            ),
        ],
        ext={
            "nyc.dob_now_job_filing_number": norm(dob_now_row.get("job_filing_number")),
            "nyc.pluto_numbldgs": norm(row_get(hero_parcel_row, "NumBldgs")),
        },
    )

    permit = Permit(
        canonical_id=permit_id,
        building_ref=building_id,
        parcel_ref=parcel_id,
        permit_type=norm(permit_row.get("permit_type")) or None,
        job_type=norm(permit_row.get("job_type")) or None,
        permit_status=norm(permit_row.get("permit_status")) or None,
        work_types=work_types,
        filing_date=parse_datetime(permit_row.get("filing_date")),
        issuance_date=parse_datetime(permit_row.get("issuance_date")),
        expiration_date=parse_datetime(permit_row.get("expiration_date")),
        confidence=confidence(0.97, ResolutionMethod.exact_key, "DOB job number exact"),
        provenance=[
            Provenance(
                source_dataset="dob_permit_issuance",
                source_id=PREFERRED_PERMIT_JOB,
                domain=Domain.dm,
                source_fields=[
                    "job__",
                    "bin__",
                    "permit_type",
                    "work_type",
                    "permit_status",
                    "issuance_date",
                ],
                observed_at=source_time(permit_row.get("issuance_date")),
            )
        ],
        ext={
            "nyc.job_doc": norm(permit_row.get("job_doc___")),
            "nyc.permit_sequence": norm(permit_row.get("permit_sequence__")),
            "nyc.derived_bbl": bbl,
        },
    )

    license_type = norm(permit_row.get("permittee_s_license_type"))
    license_id = norm(permit_row.get("permittee_s_license__"))
    contractor_native = f"{license_type}-{license_id}" if license_type and license_id else "NOAH_OFFICE_RENOV_INC"
    contractor_id = build_canonical_id(EntityType.party, "us", "nyc", "dob_license", contractor_native)
    contractor_name = norm(permit_row.get("permittee_s_business_name")) or " ".join(
        part for part in [norm(permit_row.get("permittee_s_first_name")), norm(permit_row.get("permittee_s_last_name"))] if part
    )
    contractor = Party(
        canonical_id=contractor_id,
        name=contractor_name,
        party_type=PartyType.organization if norm(permit_row.get("permittee_s_business_name")) else PartyType.person,
        license_id=license_id or None,
        license_type=license_type or None,
        contact=norm(permit_row.get("permittee_s_phone__")) or None,
        confidence=confidence(0.95, ResolutionMethod.exact_key, "permittee license present on DOB permit row"),
        provenance=[
            Provenance(
                source_dataset="dob_permit_issuance",
                source_id=contractor_native,
                domain=Domain.dm,
                source_fields=[
                    "permittee_s_license_type",
                    "permittee_s_license__",
                    "permittee_s_business_name",
                    "permittee_s_first_name",
                    "permittee_s_last_name",
                ],
                observed_at=source_time(permit_row.get("issuance_date")),
            )
        ],
    )

    complaint_mapping = map_dob_complaint(complaint_row.get("complaint_category"))
    complaint = Event(
        canonical_id=complaint_id,
        category=complaint_mapping["category"],
        type=complaint_mapping["type"],
        timestamp=parse_datetime(complaint_row.get("date_entered")) or datetime(1970, 1, 1),
        severity=complaint_mapping["severity"],
        status=norm(complaint_row.get("status")) or None,
        geometry=point_geometry(lon, lat),
        confidence=confidence(0.92, ResolutionMethod.exact_key, "DOB complaint number exact"),
        payload={
            "complaint_category_description": complaint_mapping["description"],
            "disposition_code": norm(complaint_row.get("disposition_code")),
            "inspection_date": norm(complaint_row.get("inspection_date")),
        },
        provenance=[
            Provenance(
                source_dataset="dob_complaints_received",
                source_id=PREFERRED_COMPLAINT,
                domain=Domain.dm,
                source_fields=[
                    "complaint_number",
                    "bin",
                    "date_entered",
                    "status",
                    "complaint_category",
                    "disposition_code",
                ],
                observed_at=source_time(complaint_row.get("date_entered"), complaint_row.get("dobrundate")),
            )
        ],
        ext={
            "nyc.dob_complaint_category": norm(complaint_row.get("complaint_category")),
            "nyc.house_number": norm(complaint_row.get("house_number")),
            "nyc.house_street": norm(complaint_row.get("house_street")),
        },
    )

    traffic_points = parse_link_points(traffic_row.get("link_points"))
    if len(traffic_points) < 2:
        raise ValueError(f"Traffic link {traffic_row.get('link_id')} has no parseable link_points")
    collision_lat_for_distance = parse_float(collision_row.get("latitude"))
    collision_lon_for_distance = parse_float(collision_row.get("longitude"))
    if collision_lat_for_distance is None or collision_lon_for_distance is None:
        raise ValueError(f"Collision {collision_row.get('collision_id')} has no usable point")
    nearest_m = min(
        approx_distance_m(collision_lat_for_distance, collision_lon_for_distance, point_lat, point_lon)
        for point_lat, point_lon in traffic_points
    )
    road_id = build_canonical_id(EntityType.road_segment, "us", "nyc", "link", norm(traffic_row.get("link_id")))
    collision_id = build_canonical_id(EntityType.event, "us", "nyc", "collision", norm(collision_row.get("collision_id")))

    road = RoadSegment(
        canonical_id=road_id,
        name=norm(traffic_row.get("link_name")) or None,
        owner=norm(traffic_row.get("owner")) or None,
        geometry=line_geometry(traffic_points),
        confidence=confidence(1.0, ResolutionMethod.exact_key, "DOT traffic speed link_id exact"),
        provenance=[
            Provenance(
                source_dataset="dot_traffic_speeds",
                source_id=norm(traffic_row.get("link_id")),
                domain=Domain.mobility,
                source_fields=["link_id", "link_name", "link_points", "speed", "travel_time", "data_as_of"],
                observed_at=source_time(traffic_row.get("data_as_of")),
            )
        ],
        ext={
            "nyc.speed_mph": norm(traffic_row.get("speed")),
            "nyc.travel_time_sec": norm(traffic_row.get("travel_time")),
            "nyc.transcom_id": norm(traffic_row.get("transcom_id")),
        },
    )

    collision_lat = parse_float(collision_row.get("latitude"))
    collision_lon = parse_float(collision_row.get("longitude"))
    assert collision_lat is not None and collision_lon is not None
    collision = Event(
        canonical_id=collision_id,
        category=EventCategory.incident,
        type="vehicle_collision",
        timestamp=parse_crash_datetime(collision_row.get("crash_date"), collision_row.get("crash_time")),
        severity=EventSeverity.high if parse_int(collision_row.get("number_of_persons_killed")) else EventSeverity.medium,
        status="recorded",
        geometry=point_geometry(collision_lon, collision_lat),
        confidence=confidence(0.90, ResolutionMethod.exact_key, "NYC collisions collision_id exact"),
        payload={
            "persons_injured": parse_int(collision_row.get("number_of_persons_injured")),
            "persons_killed": parse_int(collision_row.get("number_of_persons_killed")),
            "contributing_factor_vehicle_1": norm(collision_row.get("contributing_factor_vehicle_1")),
        },
        provenance=[
            Provenance(
                source_dataset="motor_vehicle_collisions_crashes",
                source_id=norm(collision_row.get("collision_id")),
                domain=Domain.public_safety,
                source_fields=[
                    "collision_id",
                    "crash_date",
                    "crash_time",
                    "latitude",
                    "longitude",
                    "number_of_persons_injured",
                    "number_of_persons_killed",
                ],
                observed_at=parse_crash_datetime(collision_row.get("crash_date"), collision_row.get("crash_time")),
            )
        ],
    )

    evtol = Resource(
        canonical_id=build_canonical_id(EntityType.resource, "us", "nyc", "fleet", "evtol-01"),
        resource_type="evtol",
        resource_status="available",
        capabilities=["rapid_assessment", "visual_overwatch"],
        confidence=confidence(1.0, ResolutionMethod.asserted, "simulated dispatch resource for Flow 2"),
        provenance=[
            Provenance(
                source_dataset="simulated_resource_stub",
                source_id="evtol-01",
                domain=Domain.synthetic,
                source_fields=["resource_type", "capabilities"],
                derivation="[Simulated] minimal Flow 2 dispatch resource",
            )
        ],
    )
    inspection_crew = Resource(
        canonical_id=build_canonical_id(EntityType.resource, "us", "nyc", "fleet", "inspection-crew-01"),
        resource_type="inspection_crew",
        resource_status="available",
        capabilities=["construction_inspection", "site_safety_review"],
        confidence=confidence(1.0, ResolutionMethod.asserted, "simulated inspection crew for Flow 2"),
        provenance=[
            Provenance(
                source_dataset="simulated_resource_stub",
                source_id="inspection-crew-01",
                domain=Domain.synthetic,
                source_fields=["resource_type", "capabilities"],
                derivation="[Simulated] minimal Flow 2 dispatch resource",
            )
        ],
    )

    edges = [
        Edge(
            src_ref=parcel_id,
            dst_ref=building_id,
            relation=Relation.has_building,
            provenance=[Provenance(source_dataset="dob_permit_issuance", source_id=PREFERRED_BIN, domain=Domain.dm)],
            confidence=confidence(parcel_link_score, parcel_link_method, f"building BIN linked to parcel through {parcel_link_method.value}"),
        ),
        Edge(
            src_ref=building_id,
            dst_ref=permit_id,
            relation=Relation.subject_of_permit,
            provenance=[Provenance(source_dataset="dob_permit_issuance", source_id=PREFERRED_PERMIT_JOB, domain=Domain.dm)],
            confidence=confidence(0.97, ResolutionMethod.exact_key, "permit row carries same BIN as building"),
        ),
        Edge(
            src_ref=permit_id,
            dst_ref=contractor_id,
            relation=Relation.performed_by,
            role="contractor",
            provenance=[
                Provenance(source_dataset="dob_permit_issuance", source_id=contractor_native, domain=Domain.dm)
            ],
            confidence=confidence(0.95, ResolutionMethod.exact_key, "permittee license present on permit row"),
        ),
        Edge(
            src_ref=complaint_id,
            dst_ref=building_id,
            relation=Relation.resolves_to,
            provenance=[Provenance(source_dataset="dob_complaints_received", source_id=PREFERRED_COMPLAINT, domain=Domain.dm)],
            confidence=confidence(0.95, ResolutionMethod.exact_key, "DOB complaint BIN matches canonical building BIN"),
        ),
        Edge(
            src_ref=collision_id,
            dst_ref=road_id,
            relation=Relation.affects,
            provenance=[
                Provenance(
                    source_dataset="motor_vehicle_collisions_crashes + dot_traffic_speeds",
                    source_id=f"{norm(collision_row.get('collision_id'))}->{norm(traffic_row.get('link_id'))}",
                    domain=Domain.mobility,
                    derivation="nearest sampled DOT traffic link to collision point",
                )
            ],
            confidence=confidence(
                0.70,
                ResolutionMethod.nearest,
                f"collision point nearest sampled DOT traffic link; approx {nearest_m:.0f} m",
            ),
        ),
    ]

    parcel_ids = {p.canonical_id for p in parcel_entities}
    owner_party_ids = set(owner_parties_by_id)
    resource_ids = {evtol.canonical_id, inspection_crew.canonical_id}
    stage_entity_ids = {
        "parcel": {*parcel_ids, *owner_party_ids},
        "permit": {*parcel_ids, *owner_party_ids, building_id, permit_id},
        "contractor": {*parcel_ids, *owner_party_ids, building_id, permit_id, contractor_id},
        "complaint": {*parcel_ids, *owner_party_ids, building_id, permit_id, contractor_id, complaint_id},
        "mobility": {*parcel_ids, *owner_party_ids, building_id, permit_id, contractor_id, complaint_id, road_id, collision_id},
        "resource": {
            *parcel_ids,
            *owner_party_ids,
            building_id,
            permit_id,
            contractor_id,
            complaint_id,
            road_id,
            collision_id,
            *resource_ids,
        },
    }
    stage_relations = {
        "parcel": {Relation.involves_party},
        "permit": {Relation.involves_party, Relation.has_building, Relation.subject_of_permit},
        "contractor": {Relation.involves_party, Relation.has_building, Relation.subject_of_permit, Relation.performed_by},
        "complaint": {Relation.involves_party, Relation.has_building, Relation.subject_of_permit, Relation.performed_by, Relation.resolves_to},
        "mobility": {
            Relation.involves_party,
            Relation.has_building,
            Relation.subject_of_permit,
            Relation.performed_by,
            Relation.resolves_to,
            Relation.affects,
        },
        "resource": {
            Relation.involves_party,
            Relation.has_building,
            Relation.subject_of_permit,
            Relation.performed_by,
            Relation.resolves_to,
            Relation.affects,
        },
    }

    edges = [*owner_edges, *edges]
    all_entities = [*parcel_entities, *owner_parties_by_id.values(), building, permit, contractor, complaint, road, collision, evtol, inspection_crew]
    entities = [e for e in all_entities if e.canonical_id in stage_entity_ids[stage]]
    edges = [e for e in edges if e.relation in stage_relations[stage]]

    entity_dicts = [AnyEntityAdapter.validate_python(e.model_dump(mode="json")).model_dump(mode="json") for e in entities]
    edge_dicts = [Edge.model_validate(e.model_dump(mode="json")).model_dump(mode="json") for e in edges]
    summary = {
        "stage": stage,
        "cascade": {
            "bin": PREFERRED_BIN,
            "bbl": bbl,
            "permit_job": PREFERRED_PERMIT_JOB,
            "complaint_number": PREFERRED_COMPLAINT,
            "address": norm(row_get(hero_parcel_row, "Address")),
            "contractor": contractor_name,
            "contractor_license_type": license_type,
            "contractor_license_id": license_id,
            "complaint_category": norm(complaint_row.get("complaint_category")),
            "complaint_category_description": complaint_mapping["description"],
            "complaint_event_category": complaint_mapping["category"].value,
            "complaint_event_type": complaint_mapping["type"],
            "complaint_event_severity": complaint_mapping["severity"].value,
            "permit_issuance_date": norm(permit_row.get("issuance_date")),
            "complaint_date_entered": norm(complaint_row.get("date_entered")),
            "timing": "permit_then_complaint",
            "permit_to_complaint_days": (
                (parse_datetime(complaint_row.get("date_entered")) - parse_datetime(permit_row.get("issuance_date"))).days
                if parse_datetime(complaint_row.get("date_entered")) and parse_datetime(permit_row.get("issuance_date"))
                else None
            ),
        },
        "mobility": {
            "collision_id": norm(collision_row.get("collision_id")),
            "road_link_id": norm(traffic_row.get("link_id")),
            "nearest_m": round(nearest_m, 1),
        },
        "counts": {"entities": len(entity_dicts), "edges": len(edge_dicts)},
        "mappluto": {
            "scope": "MN block 1060",
            "parcel_rows": len(parcel_entities),
            "polygon_rows": polygon_count,
            "owner_parties": len(owner_parties_by_id),
            "hero_land_use": parcel.land_use,
            "hero_zoning": parcel.zoning,
            "hero_parcel_confidence": parcel.confidence.model_dump(mode="json"),
            "hero_geometry_type": parcel.geometry.type.value if parcel.geometry else None,
        },
    }
    return entity_dicts, edge_dicts, summary


def write_artifacts(entity_dicts: list[dict], edge_dicts: list[dict], summary: dict[str, object]) -> None:
    out_dir = ROOT / "artifacts" / "nyc_flow2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entities.json").write_text(json.dumps(entity_dicts, indent=2), encoding="utf-8")
    (out_dir / "edges.json").write_text(json.dumps(edge_dicts, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and gate the NYC Flow 2 canonical slice.")
    parser.add_argument(
        "--stage",
        choices=(*STAGE_ORDER, "all"),
        default="resource",
        help="Adapter stage to emit. 'resource' is the full green Flow 2 slice.",
    )
    parser.add_argument(
        "--run-stages",
        action="store_true",
        help="Run the harness after each Flow 2 build-order stage and return the final stage exit code.",
    )
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON outputs under artifacts/nyc_flow2.")
    args = parser.parse_args()

    if args.run_stages:
        final_report = None
        final_payload = None
        for stage in STAGE_ORDER:
            entity_dicts, edge_dicts, summary = build_entities_and_edges(stage)
            report = run_harness(entity_dicts, edge_dicts)
            print_report(report, f"NYC Flow 2 adapter stage: {stage}")
            print(json.dumps(summary, indent=2))
            final_report = report
            final_payload = (entity_dicts, edge_dicts, summary)
        if args.write_artifacts and final_payload is not None:
            write_artifacts(*final_payload)
        return final_report.exit_code if final_report is not None else 1

    entity_dicts, edge_dicts, summary = build_entities_and_edges(args.stage)
    if args.write_artifacts:
        write_artifacts(entity_dicts, edge_dicts, summary)

    report = run_harness(entity_dicts, edge_dicts)
    print_report(report, f"NYC Flow 2 real-data adapter slice ({canonical_stage(args.stage)})")
    print(json.dumps(summary, indent=2))
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

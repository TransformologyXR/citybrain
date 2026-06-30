"""
TXR City Brain — Canonical Schema v1 (Pydantic v2)
==================================================

The L2 canonical entity model. This is the *contract* the graph (L3) and the
agent (L5) read. City-specific variation is absorbed below this layer by
adapters; this core never changes when a new city is added.

Design decisions (settled in design review + red-pen):
  - core + provenance envelope: a small typed core every city maps into,
    plus the untouched source record(s) carried as provenance.
  - identity triad on every entity: canonical_id + provenance[] + confidence.
    Raw source keys live in provenance[].source_id (one per source); the
    canonical_id is the constructed identity. No per-entity native_key.
  - Party-with-role: one Party entity; the role (owner/contractor/applicant/
    inspector/buyer/seller/...) lives on the EDGE, never as a column.
  - Events use a TWO-LEVEL taxonomy: category (closed, city-agnostic enum) +
    type (open string, source/city-specific). Aligns with the action core's
    entry points: observation->Query, incident/request->Incident, planned->Plan.
  - confidence-bearing relationships are EDGES (so the 0.70 geometry-only
    resolution lives on the edge); intrinsic 1:1 parent refs stay inline.
  - DLD/DM unified at the entity layer; domain provenance kept per field.
  - full geometry (Point/LineString/Polygon/MultiPolygon) with a guaranteed
    representative point fallback.
  - reserved entities: named + minimal + status='reserved'.

Canonical ID format:  {entity_type}:{country}-{city}:{id_system}:{native_id}
  e.g.  parcel:us-nyc:bbl:2054800111   building:us-nyc:bin:3395389
        party:us-nyc:dob_license:GC-0037136   road:us-nyc:link:4362249

Run directly to emit JSON Schema and validate worked examples:
    python txr_citybrain_schema_v1.py
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import sys
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter, computed_field, field_validator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    # core (in-scope for the Flow 2 golden path)
    parcel = "parcel"
    building = "building"
    permit = "permit"
    party = "party"
    inspection = "inspection"
    road_segment = "road_segment"
    event = "event"
    resource = "resource"          # core, minimal footprint in v1 (eVTOL + crew)
    # reserved (named + thin; not populated/gated in v1)
    unit = "unit"
    development = "development"     # DLD calls this "project"
    sensor = "sensor"
    infrastructure_asset = "infrastructure_asset"
    transit_node = "transit_node"


class EntityStatus(str, Enum):
    active = "active"
    reserved = "reserved"


class Domain(str, Enum):
    """Source domain — kept on every provenance record so a unified entity still
    carries which silo each field came from (replaces Phase 1's tool-level
    PROHIBITED_COMBOS with field-level provenance)."""
    land = "land"
    dld = "dld"                    # Dubai Land Dept — financial / transactional
    dm = "dm"                      # Dubai Municipality / DOB — structural / permits
    civic = "civic"
    mobility = "mobility"
    public_safety = "public_safety"
    utility = "utility"
    perception = "perception"
    base_layer = "base_layer"
    synthetic = "synthetic"


class ResolutionMethod(str, Enum):
    """How an entity's identity (or a resolution edge) was established — drives
    the confidence score. The thing Phase 1's bare-string model could not do."""
    exact_key = "exact_key"
    derived_key = "derived_key"
    point_in_polygon = "point_in_polygon"
    nearest = "nearest"
    fuzzy_match = "fuzzy_match"
    asserted = "asserted"
    exact_bin = "exact_bin"
    job_number = "job_number"
    complaint_number = "complaint_number"
    license_number = "license_number"
    address_fallback = "address_fallback"
    spatial_fallback = "spatial_fallback"
    name_hash = "name_hash"


class GeometryType(str, Enum):
    point = "Point"
    line_string = "LineString"
    polygon = "Polygon"
    multi_polygon = "MultiPolygon"


class PartyType(str, Enum):
    person = "person"
    organization = "organization"


class EventCategory(str, Enum):
    """Closed, city-agnostic top-level class — the stable contract the agent
    routes on. Aligns with the action core's entry points."""
    observation = "observation"    # reading / measurement / detection -> Query
    incident = "incident"          # something wrong / demands response -> Incident
    request = "request"            # citizen-initiated service request -> Incident
    transaction = "transaction"    # economic / legal event (sale/rent/valuation)
    planned = "planned"            # scheduled event (parade/closure/shutdown) -> Plan


class EventSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Relation(str, Enum):
    """Typed graph edges (L3 multiplex). Party roles are explicit relations;
    involves_party + `role` is the open-ended escape hatch so a new city's role
    (e.g. Dubai 'consultant') is new edge DATA, not a schema change."""
    has_building = "has_building"          # parcel  -> building
    has_unit = "has_unit"                  # building -> unit
    part_of = "part_of"                    # parcel/building -> development
    developed_by = "developed_by"          # development -> party
    subject_of_permit = "subject_of_permit"  # building -> permit
    filed_by = "filed_by"                  # permit -> party (owner)
    performed_by = "performed_by"          # permit -> party (contractor/permittee)
    designed_by = "designed_by"            # permit -> party (applicant / PE-RA)
    involves_party = "involves_party"      # permit/event -> party (+ role string)
    requires_inspection = "requires_inspection"  # permit -> inspection
    conducted_by = "conducted_by"          # inspection -> party (inspector, optional)
    near = "near"                          # spatial proximity
    resolves_to = "resolves_to"            # event -> resolved entity (carries confidence)
    affects = "affects"                    # event -> road_segment / asset
    depends_on = "depends_on"              # building/unit/asset -> asset (cascade)
    observed_by = "observed_by"            # event -> sensor
    dispatches = "dispatches"              # event/plan -> resource


# ─────────────────────────────────────────────────────────────────────────────
# Value objects (the identity triad + geometry)
# ─────────────────────────────────────────────────────────────────────────────

class Geometry(BaseModel):
    """GeoJSON-style geometry. Full geometry where the source/base layer provides
    it; a representative `point` ([lon, lat]) is ALWAYS present so the registry
    can spatially resolve anything, even key-less records.
    (`coordinates` is intentionally loose for v1; tighten to per-type unions later.)"""
    type: GeometryType
    coordinates: Any = Field(description="GeoJSON coordinates; shape depends on `type`.")
    point: list[float] = Field(
        description="Guaranteed representative point [lon, lat].",
        min_length=2, max_length=2,
    )
    crs: str = Field(default="EPSG:4326")

    @field_validator("point")
    @classmethod
    def _lonlat(cls, v: list[float]) -> list[float]:
        lon, lat = v
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"point out of range: lon={lon}, lat={lat}")
        return v


class Provenance(BaseModel):
    """Field-level provenance. One record per contributing source. Carries the
    raw source key (`source_id`) — this is where native keys live now."""
    source_dataset: str
    source_id: str = Field(description="Native record id/key in that source (e.g. BBL, BIN).")
    domain: Domain
    source_fields: list[str] = Field(default_factory=list)
    observed_at: Optional[datetime] = None
    derivation: Optional[str] = Field(default=None,
        description="How a value was derived, e.g. 'BBL = borough+block+lot'.")
    ingest_run_id: Optional[str] = None


class Confidence(BaseModel):
    """Confidence in the entity's identity (or a resolution edge), with reason.
    1.0 exact-key vs ~0.7 geometry-only is the L2 upgrade over Phase 1."""
    score: float = Field(ge=0.0, le=1.0)
    method: ResolutionMethod
    basis: str = Field(description="Human-readable reason for the score.")


CANONICAL_ID_PATTERN = r"^[a-z_]+:[a-z]{2}-[a-z]{2,4}:[a-z0-9_]+:.+$"


def build_canonical_id(entity_type: EntityType, country: str, city: str,
                       id_system: str, native_id: str) -> str:
    return f"{entity_type.value}:{country.lower()}-{city.lower()}:{id_system}:{native_id}"


CanonicalRef = str   # a reference to another canonical entity = its canonical_id


# ─────────────────────────────────────────────────────────────────────────────
# Base entity
# ─────────────────────────────────────────────────────────────────────────────

class CanonicalEntity(BaseModel):
    """Every entity = small typed core + identity triad + geometry + an `ext`
    namespace for city-specific-but-useful fields the core does not require."""
    model_config = {"use_enum_values": False, "extra": "forbid"}

    canonical_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    entity_type: EntityType
    status: EntityStatus = EntityStatus.active
    provenance: list[Provenance] = Field(default_factory=list)
    confidence: Confidence
    geometry: Optional[Geometry] = None
    ext: dict[str, Any] = Field(default_factory=dict,
        description="Namespaced extension fields, e.g. {'nyc.zonedist1': 'R3A'}.")

    @property  # convenience accessor (not serialised); raw keys live in provenance
    def primary_native_key(self) -> Optional[str]:
        return self.provenance[0].source_id if self.provenance else None


# ─────────────────────────────────────────────────────────────────────────────
# CORE entities
# ─────────────────────────────────────────────────────────────────────────────

class Parcel(CanonicalEntity):
    entity_type: Literal[EntityType.parcel] = EntityType.parcel
    land_use: Optional[str] = None
    zoning: list[str] = Field(default_factory=list)
    lot_area_sqft: Optional[float] = None
    address: Optional[str] = None
    development_ref: Optional[CanonicalRef] = None


class Building(CanonicalEntity):
    entity_type: Literal[EntityType.building] = EntityType.building
    parcel_ref: Optional[CanonicalRef] = None
    building_class: Optional[str] = None
    num_floors: Optional[float] = None
    year_built: Optional[int] = None
    units_residential: Optional[int] = None
    units_total: Optional[int] = None
    height_ft: Optional[float] = None
    development_ref: Optional[CanonicalRef] = None


class Permit(CanonicalEntity):
    entity_type: Literal[EntityType.permit] = EntityType.permit
    building_ref: Optional[CanonicalRef] = None
    parcel_ref: Optional[CanonicalRef] = None
    permit_type: Optional[str] = None
    job_type: Optional[str] = None
    permit_status: Optional[str] = None
    work_types: list[str] = Field(default_factory=list)
    filing_date: Optional[datetime] = None
    issuance_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    initial_cost: Optional[float] = None
    floor_area_sqft: Optional[float] = None
    # parties (owner/contractor/applicant) are EDGES, not fields here.


class Party(CanonicalEntity):
    """Person or organisation. Role is NOT stored here — it lives on the edge."""
    entity_type: Literal[EntityType.party] = EntityType.party
    name: str
    party_type: PartyType
    license_id: Optional[str] = Field(default=None, description="Strong key when present.")
    license_type: Optional[str] = Field(default=None, description="e.g. GC, PE, RA.")
    contact: Optional[str] = None


class Inspection(CanonicalEntity):
    """First-class; inspector optional. Target is polymorphic (permit/building/
    establishment — validated against restaurant inspection data)."""
    entity_type: Literal[EntityType.inspection] = EntityType.inspection
    target_ref: CanonicalRef = Field(description="What is inspected.")
    inspection_type: Optional[str] = None
    inspection_status: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    disposition_code: Optional[str] = None
    inspector_ref: Optional[CanonicalRef] = None   # conducted_by -> party (optional)


class RoadSegment(CanonicalEntity):
    entity_type: Literal[EntityType.road_segment] = EntityType.road_segment
    name: Optional[str] = None
    owner: Optional[str] = None
    # geometry is a LineString (traffic-speeds link_points / encoded_poly_line).
    # speed/travel-time are 'observation' Events, not fields here.


class Event(CanonicalEntity):
    """The workhorse. Absorbs complaints, 311, collisions, speed readings,
    dispatches, planned events, and DLD transactions — six source types, one
    entity. Two-level taxonomy: category (closed) + type (open). Resolution to
    entities is via resolves_to / affects EDGES (which carry the confidence)."""
    entity_type: Literal[EntityType.event] = EntityType.event
    category: EventCategory
    type: str = Field(description="Specific, source/city-specific kind, e.g. "
                                  "'construction_complaint', 'vehicle_collision'.")
    timestamp: datetime
    severity: Optional[EventSeverity] = None
    status: Optional[str] = Field(default=None, description="Lifecycle: open/closed/resolved.")
    value: Optional[float] = Field(default=None, description="e.g. transaction value.")
    payload: dict[str, Any] = Field(default_factory=dict)
    # resolution to entities is via EDGES (resolves_to / affects / observed_by).


class Resource(CanonicalEntity):
    """Core, MINIMAL in v1: just the dispatchable units the golden path needs
    (an eVTOL and an inspection crew). Full fleet model is reserved."""
    entity_type: Literal[EntityType.resource] = EntityType.resource
    resource_type: str = Field(description="e.g. evtol, inspection_crew, ambulance.")
    resource_status: Optional[str] = None
    home_ref: Optional[CanonicalRef] = None
    capabilities: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# RESERVED entities (declared + thin; not populated or gated in v1)
# ─────────────────────────────────────────────────────────────────────────────

class Unit(CanonicalEntity):
    """Sub-building: condo/apartment/commercial unit. Flow 1, Dubai DLD."""
    entity_type: Literal[EntityType.unit] = EntityType.unit
    status: EntityStatus = EntityStatus.reserved
    building_ref: Optional[CanonicalRef] = None
    unit_designator: Optional[str] = None
    use: Optional[str] = None
    area_sqft: Optional[float] = None


class Development(CanonicalEntity):
    """Named development grouping spanning multiple parcels/buildings. DLD
    'project'; LL84 multi-building 'property'. developed_by a Party."""
    entity_type: Literal[EntityType.development] = EntityType.development
    status: EntityStatus = EntityStatus.reserved
    name: Optional[str] = None
    developer_ref: Optional[CanonicalRef] = None
    parcel_refs: list[CanonicalRef] = Field(default_factory=list)


class Sensor(CanonicalEntity):
    """Fixed observation device — camera/pedestrian/air/parking. Flows 4, 7.
    Lowest grounding (no NYC donor); reshape when real sensor data lands."""
    entity_type: Literal[EntityType.sensor] = EntityType.sensor
    status: EntityStatus = EntityStatus.reserved
    sensor_type: Optional[str] = None
    observes: list[str] = Field(default_factory=list)


class InfrastructureAsset(CanonicalEntity):
    """Fixed utility/infra node — substation/pump/hydrant/main. Participates in
    the depends_on cascade (a GENERAL edge). Flow 5."""
    entity_type: Literal[EntityType.infrastructure_asset] = EntityType.infrastructure_asset
    status: EntityStatus = EntityStatus.reserved
    asset_type: Optional[str] = None
    capacity: Optional[float] = None


class TransitNode(CanonicalEntity):
    """Transit stop/station (+ routes). Flow-4 horizon (GTFS/TfL/RTA)."""
    entity_type: Literal[EntityType.transit_node] = EntityType.transit_node
    status: EntityStatus = EntityStatus.reserved
    node_type: Optional[str] = None
    routes: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Edges (L3 multiplex graph)
# ─────────────────────────────────────────────────────────────────────────────

class Edge(BaseModel):
    """A typed, provenanced relationship. `role` carries the open-ended refinement
    (owner/contractor/applicant/buyer/seller/consultant/...) so a new city's role
    is data, not a schema change. `confidence` lets resolution edges carry their
    own score (e.g. 0.70 geometry-only)."""
    model_config = {"extra": "forbid"}

    src_ref: CanonicalRef
    dst_ref: CanonicalRef
    relation: Relation
    role: Optional[str] = Field(default=None,
        description="Refinement for involves_party etc. (e.g. 'consultant').")
    provenance: list[Provenance] = Field(default_factory=list)
    confidence: Optional[Confidence] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


# Discriminated union over every entity — lets the harness/loaders parse a mixed
# collection and dispatch to the right model by `entity_type`.
AnyEntity = Annotated[
    Union[Parcel, Building, Permit, Party, Inspection, RoadSegment, Event, Resource,
          Unit, Development, Sensor, InfrastructureAsset, TransitNode],
    Field(discriminator="entity_type"),
]
AnyEntityAdapter = TypeAdapter(AnyEntity)

ENTITY_MODELS = [
    Parcel, Building, Permit, Party, Inspection, RoadSegment, Event, Resource,
    Unit, Development, Sensor, InfrastructureAsset, TransitNode,
]


# ─────────────────────────────────────────────────────────────────────────────
# __main__ : emit JSON Schema + validate worked examples from real NYC data
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    all_models = {m.__name__: m for m in ENTITY_MODELS}
    all_models["Edge"] = Edge
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "title": "TXR City Brain — Canonical Schema v1", "$defs": {}}
    for name, model in all_models.items():
        s = model.model_json_schema(ref_template="#/$defs/{model}")
        schema["$defs"].update(s.pop("$defs", {}))
        schema["$defs"][name] = s
    with open("txr_citybrain_schema_v1.schema.json", "w") as f:
        json.dump(schema, f, indent=2)
    print(f"✓ wrote txr_citybrain_schema_v1.schema.json ({len(schema['$defs'])} definitions)")

    # Worked Building from the real DOB-NOW + PLUTO rows (no native_key; key in provenance)
    bldg = Building(
        canonical_id=build_canonical_id(EntityType.building, "us", "nyc", "bin", "3395389"),
        parcel_ref=build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", "3011727502"),
        building_class="A5", num_floors=4, units_residential=96, units_total=96,
        geometry=Geometry(type=GeometryType.point, coordinates=[-73.968474, 40.673077],
                          point=[-73.968474, 40.673077]),
        confidence=Confidence(score=0.95, method=ResolutionMethod.exact_key,
                              basis="BIN exact across DOB; parcel link via BBL exact"),
        provenance=[
            Provenance(source_dataset="dob_now_filings", source_id="3395389", domain=Domain.dm,
                       source_fields=["bin", "bbl", "proposed_no_of_stories"],
                       observed_at=datetime(2022, 12, 21)),
            Provenance(source_dataset="pluto", source_id="3011727502", domain=Domain.land,
                       source_fields=["bldgclass", "numfloors"], derivation="BBL join"),
        ],
        ext={"nyc.nta": "Prospect Heights"},
    )

    # Collision Event: two-level taxonomy + severity; resolution is an EDGE (carries 0.70)
    collision = Event(
        canonical_id=build_canonical_id(EntityType.event, "us", "nyc", "collision", "4455765"),
        category=EventCategory.incident, type="vehicle_collision",
        timestamp=datetime(2021, 9, 11, 2, 39), severity=EventSeverity.high, status="closed",
        geometry=Geometry(type=GeometryType.point, coordinates=[-73.970024, 40.62179],
                          point=[-73.970024, 40.62179]),
        confidence=Confidence(score=0.90, method=ResolutionMethod.exact_key,
                              basis="collision record id is unique"),
        payload={"persons_injured": 2, "contributing_factor": "Aggressive Driving/Road Rage"},
        provenance=[Provenance(source_dataset="motor_vehicle_collisions", source_id="4455765",
                               domain=Domain.public_safety)],
    )
    collision_to_road = Edge(
        src_ref=collision.canonical_id,
        dst_ref=build_canonical_id(EntityType.road_segment, "us", "nyc", "link", "4362249"),
        relation=Relation.affects,
        confidence=Confidence(score=0.70, method=ResolutionMethod.nearest,
                              basis="lat/lon only; no link_id or BBL on the record"),
    )

    # Role-on-edge: permit performed_by a licensed contractor (Party)
    contractor = Party(
        canonical_id=build_canonical_id(EntityType.party, "us", "nyc", "dob_license", "GC-0037136"),
        name="John Shen", party_type=PartyType.person, license_id="0037136", license_type="GC",
        confidence=Confidence(score=0.95, method=ResolutionMethod.exact_key,
                              basis="GC license uniquely identifies contractor across permits"),
        provenance=[Provenance(source_dataset="dob_permit_issuance", source_id="0037136",
                               domain=Domain.dm, source_fields=["permittee_s_license__"])],
    )
    performed_by = Edge(src_ref="permit:us-nyc:dob_job:340733647", dst_ref=contractor.canonical_id,
                        relation=Relation.performed_by, role="contractor",
                        confidence=Confidence(score=0.95, method=ResolutionMethod.exact_key,
                                              basis="permittee license present on permit row"))

    for label, obj in [("Building", bldg), ("Event(collision)", collision),
                       ("Party(contractor)", contractor),
                       ("Edge(affects 0.70)", collision_to_road),
                       ("Edge(performed_by)", performed_by)]:
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
        print(f"✓ {label:<20} validates + round-trips")

    # AnyEntity discriminated union: parse a mixed bag by entity_type
    mixed = [json.loads(bldg.model_dump_json()), json.loads(collision.model_dump_json()),
             json.loads(contractor.model_dump_json())]
    parsed = [AnyEntityAdapter.validate_python(d) for d in mixed]
    print(f"✓ AnyEntity union parsed {len(parsed)} mixed entities → "
          f"{[type(p).__name__ for p in parsed]}")
    print(f"✓ primary_native_key (Building) = {bldg.primary_native_key}  (from provenance)")
    print("\n✓ canonical schema v1 (post red-pen) — all examples valid against real NYC data")

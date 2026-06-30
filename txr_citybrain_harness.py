"""
TXR City Brain — Acceptance Harness (Gate a2)
=============================================

The single source of truth for "is it green?" (Rule 8). Fed the canonical
entities + edges an adapter produces (as JSON-able dicts), it runs two tiers of
checks and prints a RED/GREEN report:

  TIER 1 — INVARIANTS: must hold for whatever data IS present.
    G-SCHEMA  every entity/edge validates against the Pydantic schema
    G-ID      canonical_id matches its entity_type prefix + the id pattern
    G-TRIAD   identity triad present: provenance[] + confidence + basis
    G-GEO     locatable entities carry geometry with a valid representative point
    G-REF     referential integrity: every *_ref and edge endpoint resolves
    G-EDGE    resolution edges (resolves_to/affects/near) carry their confidence

  TIER 2 — FLOW 2 ACCEPTANCE: the golden path's definition-of-done. RED now
  (empty stub), each turning GREEN as an adapter lands the needed entity/edge.
    F2-PARCEL / F2-BUILDING / F2-PERMIT / F2-COMPLAINT / F2-CONTRACTOR /
    F2-RESOURCE / F2-MOBILITY  — the pieces exist
    F2-CASCADE  — they are CONNECTED: a construction complaint resolves_to a
                  building, that building is subject_of a permit performed_by a
                  party, and the building sits on a parcel. (The golden path.)

This is join point #1: the same harness validates the synthetic-data pipeline.

Usage as a gate (CI):  report = run_harness(entities, edges); sys.exit(report.exit_code)
Run directly for a demo across empty / good / broken stubs:  python txr_citybrain_harness.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime

from txr_citybrain_schema_v1 import (
    AnyEntityAdapter, Edge, EntityStatus, EventCategory, Relation,
    CANONICAL_ID_PATTERN, build_canonical_id, EntityType, GeometryType,
    ResolutionMethod, PartyType, EventSeverity,
    Parcel, Building, Permit, Party, Inspection, RoadSegment, Event, Resource,
    Geometry, Provenance, Confidence, Domain,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Entity types that must be locatable (carry geometry + a representative point).
SPATIAL_REQUIRED = {"parcel", "building", "road_segment", "event"}
# Edge relations that assert a resolution/association and must carry confidence.
RESOLUTION_RELATIONS = {Relation.resolves_to.value, Relation.affects.value,
                        Relation.near.value, Relation.depends_on.value}
_ID_RE = re.compile(CANONICAL_ID_PATTERN)


# ─────────────────────────────────────────────────────────────────────────────
# Report types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GateResult:
    gate_id: str
    name: str
    tier: str                 # 'invariant' | 'flow2'
    passed: bool
    checked: int = 0
    failed: int = 0
    details: list[str] = field(default_factory=list)   # up to a few samples


@dataclass
class HarnessReport:
    results: list[GateResult]

    @property
    def invariants_green(self) -> bool:
        return all(r.passed for r in self.results if r.tier == "invariant")

    @property
    def flow2_green(self) -> bool:
        return all(r.passed for r in self.results if r.tier == "flow2")

    @property
    def all_green(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.all_green else 1


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 — invariant gates
# ─────────────────────────────────────────────────────────────────────────────

def _gate_schema(entity_dicts, edge_dicts):
    """Validate everything against the Pydantic schema. Returns the parsed
    entities/edges plus the gate result (unparseable items are excluded from
    later gates, but counted as failures here)."""
    entities, edges = [], []
    details, failed = [], 0
    for i, d in enumerate(entity_dicts):
        try:
            entities.append(AnyEntityAdapter.validate_python(d))
        except Exception as e:
            failed += 1
            if len(details) < 4:
                details.append(f"entity[{i}] {d.get('canonical_id','?')}: {str(e).splitlines()[0]}")
    for i, d in enumerate(edge_dicts):
        try:
            edges.append(Edge.model_validate(d))
        except Exception as e:
            failed += 1
            if len(details) < 4:
                details.append(f"edge[{i}]: {str(e).splitlines()[0]}")
    n = len(entity_dicts) + len(edge_dicts)
    return entities, edges, GateResult("G-SCHEMA", "Schema validation", "invariant",
                                       failed == 0, n, failed, details)


def _gate_id(entities):
    failed, details = 0, []
    for e in entities:
        cid = e.canonical_id
        prefix = cid.split(":", 1)[0]
        ok = bool(_ID_RE.match(cid)) and prefix == e.entity_type.value
        if not ok:
            failed += 1
            if len(details) < 4:
                details.append(f"{cid}: prefix '{prefix}' != type '{e.entity_type.value}' or bad pattern")
    return GateResult("G-ID", "Canonical-id well-formed", "invariant",
                      failed == 0, len(entities), failed, details)


def _gate_triad(entities):
    failed, details = 0, []
    for e in entities:
        problems = []
        if not e.provenance:
            problems.append("no provenance")
        if e.confidence is None:
            problems.append("no confidence")
        elif not (e.confidence.basis or "").strip():
            problems.append("empty confidence.basis")
        if problems:
            failed += 1
            if len(details) < 4:
                details.append(f"{e.canonical_id}: {', '.join(problems)}")
    return GateResult("G-TRIAD", "Identity triad present", "invariant",
                      failed == 0, len(entities), failed, details)


def _gate_geo(entities):
    failed, details, checked = 0, [], 0
    for e in entities:
        if e.entity_type.value not in SPATIAL_REQUIRED:
            continue
        if e.status == EntityStatus.reserved:
            continue
        checked += 1
        if e.geometry is None or e.geometry.point is None or len(e.geometry.point) != 2:
            failed += 1
            if len(details) < 4:
                details.append(f"{e.canonical_id}: locatable type with no geometry/point")
    return GateResult("G-GEO", "Locatable entities have geometry", "invariant",
                      failed == 0, checked, failed, details)


def _gate_ref(entities, edges, registry):
    """Every *_ref / *_refs on an entity, and every edge endpoint, resolves to a
    known entity id."""
    failed, details, checked = 0, [], 0
    for e in entities:
        data = e.model_dump()
        for fname, val in data.items():
            if fname == "canonical_id" or val is None:
                continue
            if fname.endswith("_ref") and isinstance(val, str):
                checked += 1
                if val not in registry:
                    failed += 1
                    if len(details) < 5:
                        details.append(f"{e.canonical_id}.{fname} -> missing {val}")
            elif fname.endswith("_refs") and isinstance(val, list):
                for v in val:
                    checked += 1
                    if v not in registry:
                        failed += 1
                        if len(details) < 5:
                            details.append(f"{e.canonical_id}.{fname} -> missing {v}")
    for k, edge in enumerate(edges):
        for end in ("src_ref", "dst_ref"):
            checked += 1
            ref = getattr(edge, end)
            if ref not in registry:
                failed += 1
                if len(details) < 5:
                    details.append(f"edge[{k}] {edge.relation.value}.{end} -> missing {ref}")
    return GateResult("G-REF", "Referential integrity", "invariant",
                      failed == 0, checked, failed, details)


def _gate_edge(edges):
    """Resolution/association edges must carry their confidence (the L2 value-add:
    a 0.70 geometry-only link has to be on the edge, not implied)."""
    failed, details, checked = 0, [], 0
    for k, edge in enumerate(edges):
        if edge.relation.value in RESOLUTION_RELATIONS:
            checked += 1
            if edge.confidence is None:
                failed += 1
                if len(details) < 4:
                    details.append(f"edge[{k}] {edge.relation.value} ({edge.src_ref} -> "
                                   f"{edge.dst_ref}) carries no confidence")
    return GateResult("G-EDGE", "Resolution edges carry confidence", "invariant",
                      failed == 0, checked, failed, details)


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 — Flow 2 acceptance expectations
# ─────────────────────────────────────────────────────────────────────────────

def _active(entities, etype):
    return [e for e in entities if e.entity_type.value == etype
            and e.status != EntityStatus.reserved]


def _is_dob_complaint_event(entity):
    if entity.entity_type.value != "event" or entity.category != EventCategory.incident:
        return False
    if ":dob_complaint:" in entity.canonical_id:
        return True
    if "complaint" in (entity.type or ""):
        return True
    ext = getattr(entity, "ext", {}) or {}
    if ext.get("nyc.dob_complaint_category"):
        return True
    for provenance in getattr(entity, "provenance", []) or []:
        dataset = provenance.source_dataset or ""
        if "dob" in dataset and "complaint" in dataset:
            return True
    return False


def _flow2_presence(entities, edges):
    out = []

    def present(gate_id, name, items, hint):
        ok = len(items) >= 1
        return GateResult(gate_id, name, "flow2", ok, 1, 0 if ok else 1,
                          [] if ok else [f"none present — {hint}"])

    parcels = _active(entities, "parcel")
    buildings = _active(entities, "building")
    permits = _active(entities, "permit")
    resources = _active(entities, "resource")
    complaints = [e for e in _active(entities, "event") if _is_dob_complaint_event(e)]
    contractor_edges = [e for e in edges if e.relation == Relation.performed_by]
    mobility_edges = [e for e in edges if e.relation == Relation.affects]

    out.append(present("F2-PARCEL", "≥1 parcel", parcels, "PLUTO adapter"))
    out.append(present("F2-BUILDING", "≥1 building", buildings, "PLUTO/DOB adapter"))
    out.append(present("F2-PERMIT", "≥1 permit", permits, "DOB filings adapter"))
    out.append(present("F2-COMPLAINT", "≥1 construction complaint", complaints,
                       "DOB complaints adapter (category=incident, type~complaint)"))
    out.append(present("F2-CONTRACTOR", "≥1 performed_by edge (contractor)", contractor_edges,
                       "permit→party role edge"))
    out.append(present("F2-RESOURCE", "≥1 resource (eVTOL/crew)", resources,
                       "minimal Resource for cuOpt dispatch"))
    out.append(present("F2-MOBILITY", "≥1 affects edge (event→road)", mobility_edges,
                       "collision/closure → road segment"))
    return out


def _flow2_cascade(entities, edges, registry):
    """The golden path is CONNECTED: a construction complaint resolves_to a
    building; that building is subject_of a permit (edge or permit.building_ref)
    AND performed_by a party; and the building sits on a parcel."""
    complaints = [e for e in entities if _is_dob_complaint_event(e)]
    resolves = [e for e in edges if e.relation == Relation.resolves_to]
    subj = [e for e in edges if e.relation == Relation.subject_of_permit]
    perf = {e.src_ref for e in edges if e.relation == Relation.performed_by}

    def building_has_permit(bid):
        if any(e.src_ref == bid for e in subj):  # building -subject_of_permit-> permit
            return True
        for p in entities:  # or a permit pointing back at the building
            if p.entity_type.value == "permit" and getattr(p, "building_ref", None) == bid:
                return True
        return False

    def permit_of_building(bid):
        ids = {e.dst_ref for e in subj if e.src_ref == bid}
        ids |= {p.canonical_id for p in entities if p.entity_type.value == "permit"
                and getattr(p, "building_ref", None) == bid}
        return ids

    for c in complaints:
        for r in resolves:
            if r.src_ref != c.canonical_id:
                continue
            b = registry.get(r.dst_ref)
            if b is None or b.entity_type.value != "building":
                continue
            if getattr(b, "parcel_ref", None) not in registry:
                continue
            if not building_has_permit(b.canonical_id):
                continue
            if not (permit_of_building(b.canonical_id) & perf):
                continue
            return GateResult("F2-CASCADE", "Golden path connected", "flow2", True, 1, 0,
                              [f"{c.canonical_id} → {b.canonical_id} → permit → contractor → parcel ✓"])
    return GateResult("F2-CASCADE", "Golden path connected", "flow2", False, 1, 1,
                      ["no complete complaint→building→permit→contractor(+parcel) chain found"])


# ─────────────────────────────────────────────────────────────────────────────
# Runner + printer
# ─────────────────────────────────────────────────────────────────────────────

def run_harness(entity_dicts, edge_dicts) -> HarnessReport:
    entities, edges, g_schema = _gate_schema(entity_dicts, edge_dicts)
    registry = {e.canonical_id: e for e in entities}

    results = [g_schema, _gate_id(entities), _gate_triad(entities), _gate_geo(entities),
               _gate_ref(entities, edges, registry), _gate_edge(edges)]
    results += _flow2_presence(entities, edges)
    results.append(_flow2_cascade(entities, edges, registry))
    return HarnessReport(results)


def print_report(report: HarnessReport, title: str):
    bar = "─" * 66
    print(f"\n{bar}\n  {title}\n{bar}")
    for tier, label in [("invariant", "TIER 1 — INVARIANTS"), ("flow2", "TIER 2 — FLOW 2 ACCEPTANCE")]:
        print(f"  {label}")
        for r in [x for x in report.results if x.tier == tier]:
            tag = "GREEN" if r.passed else " RED "
            mark = "✓" if r.passed else "✗"
            print(f"    [{tag}] {mark} {r.gate_id:<12} {r.name:<34} "
                  f"({r.checked - r.failed}/{r.checked} ok)")
            for d in r.details:
                print(f"             ↳ {d}")
    inv = "GREEN" if report.invariants_green else "RED"
    f2 = "GREEN" if report.flow2_green else "RED"
    overall = "GREEN" if report.all_green else "RED"
    print(f"  {bar}")
    print(f"  invariants: {inv}   ·   flow-2: {f2}   ·   OVERALL: {overall}   (exit {report.exit_code})")


# ─────────────────────────────────────────────────────────────────────────────
# Demo stubs: empty (red expectations) · good (green) · broken (red invariants)
# ─────────────────────────────────────────────────────────────────────────────

def _conf(score, method, basis):
    return Confidence(score=score, method=method, basis=basis)


def _pt(lon, lat):
    return Geometry(type=GeometryType.point, coordinates=[lon, lat], point=[lon, lat])


def good_stub():
    """A minimal but CONNECTED Flow 2 cascade, built from real NYC-shaped values."""
    parcel = Parcel(
        canonical_id=build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", "3011727502"),
        land_use="02 Multi-Family", geometry=_pt(-73.9685, 40.6731),
        confidence=_conf(1.0, ResolutionMethod.exact_key, "BBL exact"),
        provenance=[Provenance(source_dataset="pluto", source_id="3011727502", domain=Domain.land)])
    building = Building(
        canonical_id=build_canonical_id(EntityType.building, "us", "nyc", "bin", "3395389"),
        parcel_ref=parcel.canonical_id, building_class="A5", num_floors=4,
        geometry=_pt(-73.9685, 40.6731),
        confidence=_conf(0.95, ResolutionMethod.exact_key, "BIN exact; parcel via BBL"),
        provenance=[Provenance(source_dataset="dob_now_filings", source_id="3395389", domain=Domain.dm)])
    permit = Permit(
        canonical_id=build_canonical_id(EntityType.permit, "us", "nyc", "dob_job", "340733647"),
        building_ref=building.canonical_id, parcel_ref=parcel.canonical_id,
        permit_type="NB", permit_status="ISSUED",
        confidence=_conf(0.97, ResolutionMethod.exact_key, "job number exact"),
        provenance=[Provenance(source_dataset="dob_permit_issuance", source_id="340733647", domain=Domain.dm)])
    contractor = Party(
        canonical_id=build_canonical_id(EntityType.party, "us", "nyc", "dob_license", "GC-0037136"),
        name="John Shen", party_type=PartyType.person, license_id="0037136", license_type="GC",
        confidence=_conf(0.95, ResolutionMethod.exact_key, "GC license unique"),
        provenance=[Provenance(source_dataset="dob_permit_issuance", source_id="0037136", domain=Domain.dm)])
    complaint = Event(
        canonical_id=build_canonical_id(EntityType.event, "us", "nyc", "dob_complaint", "4998881"),
        category=EventCategory.incident, type="construction_complaint",
        timestamp=datetime(2021, 1, 13), severity=EventSeverity.high, status="open",
        geometry=_pt(-73.9685, 40.6731),
        confidence=_conf(0.92, ResolutionMethod.exact_key, "complaint id unique"),
        provenance=[Provenance(source_dataset="dob_complaints", source_id="4998881", domain=Domain.dm)])
    road = RoadSegment(
        canonical_id=build_canonical_id(EntityType.road_segment, "us", "nyc", "link", "4362249"),
        name="Atlantic Ave",
        geometry=Geometry(type=GeometryType.line_string,
                          coordinates=[[-73.97, 40.673], [-73.965, 40.6735]], point=[-73.9675, 40.6732]),
        confidence=_conf(1.0, ResolutionMethod.exact_key, "link id exact"),
        provenance=[Provenance(source_dataset="dot_traffic_speeds", source_id="4362249", domain=Domain.mobility)])
    resource = Resource(
        canonical_id=build_canonical_id(EntityType.resource, "us", "nyc", "fleet", "evtol-01"),
        resource_type="evtol", resource_status="available",
        confidence=_conf(1.0, ResolutionMethod.asserted, "demo fleet asset"),
        provenance=[Provenance(source_dataset="synthetic_fleet", source_id="evtol-01", domain=Domain.synthetic)])

    entities = [parcel, building, permit, contractor, complaint, road, resource]
    edges = [
        Edge(src_ref=parcel.canonical_id, dst_ref=building.canonical_id, relation=Relation.has_building),
        Edge(src_ref=building.canonical_id, dst_ref=permit.canonical_id, relation=Relation.subject_of_permit),
        Edge(src_ref=permit.canonical_id, dst_ref=contractor.canonical_id, relation=Relation.performed_by, role="contractor"),
        Edge(src_ref=complaint.canonical_id, dst_ref=building.canonical_id, relation=Relation.resolves_to,
             confidence=_conf(0.95, ResolutionMethod.exact_key, "complaint BIN matches building")),
        Edge(src_ref=complaint.canonical_id, dst_ref=road.canonical_id, relation=Relation.affects,
             confidence=_conf(0.70, ResolutionMethod.nearest, "nearest road within buffer")),
    ]
    return ([e.model_dump(mode="json") for e in entities],
            [e.model_dump(mode="json") for e in edges])


def broken_stub():
    """Good stub, deliberately corrupted: a dangling ref, a resolution edge with
    no confidence, and an entity missing its confidence basis — to prove the
    invariant gates actually catch failures (Rule 8)."""
    entities, edges = good_stub()
    # 1) dangling parcel_ref on the building
    for e in entities:
        if e["entity_type"] == "building":
            e["parcel_ref"] = "parcel:us-nyc:bbl:0000000000"   # does not exist
        if e["entity_type"] == "resource":
            e["confidence"]["basis"] = ""                       # empty basis
    # 2) strip confidence from the 'affects' resolution edge
    for ed in edges:
        if ed["relation"] == "affects":
            ed["confidence"] = None
    return entities, edges


if __name__ == "__main__":
    print("TXR City Brain — Acceptance Harness (a2)\n"
          "Demonstrating the harness discriminates across three states:")

    empty_e, empty_x = [], []
    print_report(run_harness(empty_e, empty_x),
                 "EMPTY Flow 2 stub  → invariants pass vacuously, Flow 2 expectations RED")

    good_e, good_x = good_stub()
    print_report(run_harness(good_e, good_x),
                 "GOOD Flow 2 stub  → connected golden path, all GREEN")

    bad_e, bad_x = broken_stub()
    print_report(run_harness(bad_e, bad_x),
                 "BROKEN stub  → invariant gates catch the planted faults (RED)")

    print("\nThe harness exists before the data (Rule 7). As adapters land each entity/edge,\n"
          "the Flow 2 row turns GREEN — that progression IS the a2→G1 gate.")

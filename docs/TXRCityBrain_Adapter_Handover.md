# TXR City Brain — Adapter Handover (Codex build spec)

*The engineering spec for building the NYC adapters (critical-path step **a3**). Read the **Onboarding** doc first for project context. You have the schema (`txr_citybrain_schema_v1.py`) and the harness (`txr_citybrain_harness.py`); this tells you exactly what to build against them, in what order, and how success is measured.*

---

## 1. Goal & definition of done

Build **per-source adapters** that map raw NYC Open Data records into **canonical entities + edges** conforming to the schema, plus the **identity resolver** that links them. Success is **not** subjective — it is the harness turning green:

```
run_harness(entities, edges)  →  exit 0  (invariants GREEN + all Flow 2 rows GREEN)
```

You are done with a3 when every Flow 2 acceptance row is green on real harvested data, the headline being **`F2-CASCADE`** (a construction complaint connected through building → permit → contractor → parcel).

**In scope:** the 7 Flow 2 datasets, the identity resolver, the entities + edges the cascade needs.
**Out of scope (do not build):** the cuGraph graph itself (that's a4), the reserved entities (Unit/Development/Sensor/InfrastructureAsset/TransitNode), the other flows, Dubai, Cosmos, building footprints (centroids suffice for v1).

---

## 2. The contract

**Input:** raw rows from NYC Open Data (Socrata), per dataset. Treat every field as a string and parse explicitly (dates and numbers are inconsistent — see §4).

**Output:** two lists of **plain dicts** (JSON-able), produced via the Pydantic models:
```python
entity_dicts = [e.model_dump(mode="json") for e in entities]
edge_dicts   = [g.model_dump(mode="json") for g in edges]
```
Every entity is one of the 8 core models; every edge is an `Edge`. Validate as you go with `AnyEntityAdapter.validate_python(...)` and `Edge.model_validate(...)`, then feed both lists to `run_harness`. The harness is the gate; nothing "passes" until it says so (Rule 8).

**Hard rules from the schema (don't fight them):**
- Raw source keys go in `provenance[].source_id`, **not** as entity fields. The `canonical_id` is constructed via `build_canonical_id(...)`.
- Every entity needs the **identity triad**: ≥1 `provenance` record, a `confidence` with a non-empty `basis`, and (for locatable types) a `geometry` with a representative `point`.
- **Party roles live on edges**, not on Permit. **Event→entity resolution lives on edges** that carry their own `confidence`.

---

## 3. Architecture

```
raw rows ──► [per-source Adapter] ──► partial canonical entities + provenance
                                          │
                              [Identity Resolver] ──► canonical_id assignment,
                                          │            cross-source MERGE, confidence
                                          ▼
                              [Edge builder] ──► role edges, resolution edges
                                          ▼
                              entities + edges ──► run_harness() ──► GREEN
```

- **One adapter per source dataset.** A small shared base is fine (parse helpers, provenance construction), but keep each adapter's field mapping explicit and readable.
- **One shared Identity Resolver** (§5) — the real core. All adapters call it to mint canonical IDs and to merge records that refer to the same real entity across sources.
- **Edge builder** derives the graph edges (§6) from the resolved entities.

---

## 4. Source-field handling (the messiness to absorb)

- **Naming variants** for the same concept: BIN = `bin` (DOB-NOW, complaints) / `bin__` (permit issuance). Permit id = `job_filing_number` (DOB-NOW) / `job__` (permit issuance). Lat/lon = `latitude`/`longitude` (collisions, 311, PLUTO) / `gis_latitude`/`gis_longitude` (permit issuance).
- **Date formats:** ISO `2022-12-15T00:00:00.000` (PLUTO, DOB-NOW); `MM/DD/YYYY` (permit issuance, complaints); `YYYYMMDDHHMMSS` e.g. `20260622000000` (the `dobrundate` field). Normalise all to `datetime`.
- **Numbers** arrive as strings; coerce and tolerate blanks → `None`.
- **Keep the raw row.** Whatever you don't map to a core field either goes to `ext['nyc.<field>']` (if useful to reason over) or is recorded in `provenance[].source_fields`. Never silently drop; never invent.

---

## 5. The Identity Resolver (the core deliverable)

This is what Phase 1 never had. It assigns canonical IDs, **merges across sources**, and scores confidence with a reason.

### 5.1 ID systems per entity
| Entity | `id_system` | `native_id` source | Notes |
|---|---|---|---|
| Parcel | `bbl` | BBL (10-digit) | from MapPLUTO; derive when absent |
| Building | `bin` | BIN | DOB sets |
| Permit | `dob_job` | job/filing number | normalise `job__`↔`job_filing_number` |
| Party | `dob_license` else `name_hash` | license # (GC/PE/RA) else hash(name+role) | license = strong key |
| Inspection | `dob_complaint` / composite | complaint/inspection id | |
| RoadSegment | `link` | `link_id` (or `transcom_id`) | |
| Event | source-specific | complaint / collision / 311 / speed id | |
| Resource | `fleet` | synthetic id | minimal stub for v1 |

Construct every id with `build_canonical_id(EntityType.X, "us", "nyc", id_system, native_id)`.

### 5.2 Key derivation
- **BBL is empty in DOB permit issuance.** Derive: `BBL = borough_code(1) + block.zfill(5) + lot.zfill(4)`. Borough code: Manhattan 1, Bronx 2, Brooklyn 3, Queens 4, Staten Island 5. Mark this provenance with `derivation="BBL = borough+block+lot"` and resolution method `derived_key`.
- **BIN → BBL** for the parcel link (DOB filings carry both; use the pair to connect Building→Parcel).

### 5.3 Geometry & the fallback resolver
- **Parcels:** real polygons from **MapPLUTO `f888-ni5f`** (`the_geom` → MultiPolygon). Always also set the representative `point` (lot centroid or PLUTO lat/lon).
- **Buildings:** representative `point` = lot centroid / PLUTO lat-lon for v1. (Footprints = Track B, not required.)
- **RoadSegments:** LineString from traffic-speeds `link_points` / `encoded_poly_line`; midpoint as `point`.
- **Key-less records (collisions, traffic, some 311):** resolve to an entity by **geometry** — point-in-polygon against MapPLUTO lot polygons (→ Parcel/Building) or nearest within a buffer (→ RoadSegment). This is a **`resolves_to` / `affects` edge**, and its confidence reflects the method.

### 5.4 Confidence assignment (use `ResolutionMethod`)
| Situation | method | score (guide) |
|---|---|---|
| BIN or BBL exact match across sources | `exact_key` | 0.95–1.0 |
| BBL derived from borough+block+lot | `derived_key` | 0.85–0.92 |
| Point inside a lot polygon | `point_in_polygon` | 0.80–0.90 |
| Nearest entity within buffer (no key) | `nearest` | 0.65–0.75 |
| Name/address fuzzy match (party w/o license) | `fuzzy_match` | 0.40–0.60 |
| Synthetic / asserted | `asserted` | 1.0 |
Every `Confidence` needs a human-readable `basis` (the harness fails on an empty basis).

### 5.5 Cross-source merge
One **Building** may appear in DOB-NOW (BIN) and PLUTO/MapPLUTO (BBL). Resolve them to **one** entity with the same `canonical_id`, carrying **one provenance record per source**. Same for a **Party** seen on multiple permits (merge on license #). The merge is the point of L2 — "the city understands the same thing across silos."

---

## 6. Per-dataset mapping

> Format: native field → canonical target. `core` = a model field; `prov` = recorded in provenance; `ext` = `ext['nyc.<field>']`. Entities/edges each adapter emits are listed.

### 6.1 PLUTO / MapPLUTO (`f888-ni5f`) → **Parcel** (+ partial Building)
| native | → | target |
|---|---|---|
| `bbl` | → | Parcel id (`id_system=bbl`); `prov.source_id` |
| `the_geom` | → | `geometry` (MultiPolygon) + `point` (centroid) |
| `landuse` | → | `core.land_use` |
| `zonedist1` (+2/3/4) | → | `core.zoning[]` |
| `lotarea` | → | `core.lot_area_sqft` |
| `address` | → | `core.address` |
| `ownername` | → | (creates a Party, role=owner, via edge — see §6.x) |
| `bldgclass`,`numfloors`,`yearbuilt`,`unitsres`,`unitstotal`,`bldgarea` | → | feed **Building** core (`building_class`, `num_floors`, `year_built`, `units_residential`, `units_total`) |
| `latitude`/`longitude`,`xcoord`/`ycoord` | → | Building/Parcel `point` fallback |
| community district, council district, etc. | → | `ext['nyc.*']` |

Emits: **Parcel** (polygon), and seeds **Building** attributes (the Building entity is completed by the DOB adapters which supply BIN).

### 6.2 DOB NOW Build — Job Application Filings (`w9ak-ipjd`) → **Building**, **Permit**, **Party**(s)
| native | → | target |
|---|---|---|
| `bin` | → | Building id (`id_system=bin`) |
| `bbl` | → | Building→Parcel link (`parcel_ref`) |
| `job_filing_number` | → | Permit id (`id_system=dob_job`) |
| `filing_status` | → | Permit `permit_status` |
| `job_type`,`work_on_floor`/work types | → | Permit `job_type`, `work_types[]` |
| `proposed_no_of_stories`,`proposed_dwelling_units` | → | Building `num_floors`, `units_*` |
| `owner_first_name`/`owner_last_name`/`owner_s_business_name`/`owner_type` | → | **Party** (person/org) + edge `permit —filed_by→ party` (role=owner) |
| `applicant_first_name`/`last_name`/`applicant_license`/`professional_title` | → | **Party** (PE/RA, `license_type`) + edge `permit —designed_by→ party` (role=applicant) |
| `filing_representative_*` | → | **Party** + edge `involves_party` (role=filing_rep) |
| `specialinspectionrequirement`,`special_inspection_agency_number`,`progressinspectionrequirement` | → | **Inspection** (requirement; inspector optional) + edge `permit —requires_inspection→ inspection` |
| `house_no`/`street_name` | → | `core.address` / `ext` |
| filing dates | → | Permit `filing_date` |

Emits: **Building**, **Permit**, **Party**(owner/applicant/filing_rep), **Inspection**, and their edges.

### 6.3 DOB Permit Issuance (`ipu4-2q9a`) → **Permit**, **Party**(contractor etc.)
| native | → | target |
|---|---|---|
| `bin__` | → | Building id (note the `__`) |
| `block`/`lot`/`borough` | → | **derive BBL** (§5.2) → Parcel link |
| `job__` (+`job_doc___`) | → | Permit id (normalise to `dob_job`) |
| `permit_type`,`permit_subtype`,`work_type`,`bldg_type` | → | Permit `permit_type`, `work_types[]` |
| `permit_status`,`filing_status` | → | Permit `permit_status` |
| `issuance_date`,`expiration_date`,`job_start_date` | → | Permit `issuance_date`,`expiration_date` (parse `MM/DD/YYYY`) |
| `permittee_s_first_name`/`last_name`/`business_name`/`license_type`/`license__` | → | **Party** (contractor/GC) + edge `permit —performed_by→ party` (role=contractor) **← this edge is required for F2-CONTRACTOR & F2-CASCADE** |
| `owner_s_*` | → | **Party** + `filed_by` (role=owner) |
| `site_safety_mgr_*`,`superintendent_*` | → | **Party** + `involves_party` (role=site_safety_manager / superintendent) |
| `gis_latitude`/`gis_longitude` | → | `point` |

Emits: **Permit** (merged with the DOB-NOW permit where job numbers match), **Party**(contractor/owner/SSM/super), edges incl. the critical `performed_by`.

### 6.4 DOB Complaints (`eabe-havv`) → **Event** (the cascade trigger)
| native | → | target |
|---|---|---|
| `complaint_number` | → | Event id (`id_system=dob_complaint`) |
| — | → | Event `category=incident`, `type="construction_complaint"` **← required for F2-COMPLAINT** |
| `bin` | → | resolve to Building → edge `event —resolves_to→ building` (confidence from BIN match) **← required for F2-CASCADE** |
| `date_entered` | → | Event `timestamp` |
| `status` | → | Event `status` |
| `complaint_category` | → | Event `type` refinement / `ext` |
| `disposition_code`,`disposition_date`,`inspection_date` | → | optional **Inspection** (disposition) on the building/permit |
| `house_number`/`house_street` | → | `ext` / address |
| `dobrundate` | → | parse `YYYYMMDDHHMMSS`; `prov` |

Emits: **Event**(construction_complaint) + `resolves_to` edge to the Building (and optional Inspection).

### 6.5 DOT Traffic Speeds (`i4gi-tjb9`) → **RoadSegment** (+ speed Events)
| native | → | target |
|---|---|---|
| `link_id` (or `transcom_id`) | → | RoadSegment id |
| `link_points`/`encoded_poly_line` | → | `geometry` (LineString) + `point` |
| `link_name` | → | `core.name` |
| `owner` | → | `core.owner` |
| `speed`,`travel_time`,`data_as_of`,`status` | → | **Event** `category=observation`, `type="traffic_speed"` (a reading on the segment) |

Emits: **RoadSegment** + observation **Event**(s).

### 6.6 Motor Vehicle Collisions (`h9gi-nx95`) → **Event** (mobility/safety signal)
| native | → | target |
|---|---|---|
| `collision_id` | → | Event id |
| — | → | Event `category=incident`, `type="vehicle_collision"` |
| `crash_date`+`crash_time` | → | Event `timestamp` |
| `latitude`/`longitude` | → | `geometry` (Point); **resolve to nearest RoadSegment → edge `affects`** (confidence ~0.70) **← contributes to F2-MOBILITY** |
| `number_of_persons_injured`/`killed`,`contributing_factor_*` | → | `payload` / `severity` |
| `on_street_name`/`cross_street_name` | → | `ext` |

Emits: **Event**(vehicle_collision) + `affects` edge to a RoadSegment.

### 6.7 311 (`erm2-nwe9`) → **Event** (broad civic signal)
| native | → | target |
|---|---|---|
| `unique_key` | → | Event id |
| `complaint_type`/`descriptor` | → | Event `type`; `category=request` (or `incident` for hazards) |
| `created_date`,`closed_date` | → | `timestamp`, `status` |
| `bbl` | → | resolve to Parcel → `resolves_to` edge (when present) |
| `latitude`/`longitude` | → | Point; geometry fallback when no BBL |
| `incident_address`,`agency`,`resolution_description` | → | `ext` / `payload` |

Emits: **Event**(request/incident) + resolution edge (BBL or geometry).

### 6.x The owner-from-PLUTO / party edges
Whenever a Party is created (owner from PLUTO `ownername`; owner/contractor/applicant from DOB), emit the Party entity **and** the role edge in the same step. Merge parties across sources on license number; fall back to `name_hash` (lower confidence, `fuzzy_match`).

---

## 7. Edges to produce (and which gates they satisfy)

| edge | from → to | source | gate |
|---|---|---|---|
| `has_building` | parcel → building | BBL↔BIN link | (structure) |
| `subject_of_permit` | building → permit | DOB sets | F2-CASCADE |
| `filed_by` | permit → party(owner) | DOB owner fields | (cascade actor) |
| `performed_by` | permit → party(contractor) | permit issuance permittee | **F2-CONTRACTOR, F2-CASCADE** |
| `designed_by` | permit → party(applicant) | DOB-NOW applicant | (cascade actor) |
| `requires_inspection` | permit → inspection | DOB-NOW inspection reqs | (optional) |
| `resolves_to` | event → building/parcel | complaint BIN / 311 BBL | **F2-CASCADE** |
| `affects` | event → road_segment | collision/traffic geometry | **F2-MOBILITY** |

Resolution edges (`resolves_to`/`affects`/`near`) **must carry `confidence`** — the harness's `G-EDGE` gate fails otherwise.

---

## 8. Build order (each step turns a harness row green)

1. **PLUTO/MapPLUTO adapter** → `F2-PARCEL` ✓, partial `F2-BUILDING`.
2. **DOB-NOW filings adapter** (BIN completes Building; permit; owner/applicant parties + edges) → `F2-BUILDING` ✓, `F2-PERMIT` ✓.
3. **DOB permit issuance adapter** (merge permit; **contractor** party + `performed_by`) → `F2-CONTRACTOR` ✓.
4. **DOB complaints adapter** (construction_complaint Event + `resolves_to` Building) → `F2-COMPLAINT` ✓.
5. **Wire the cascade** (ensure complaint→building→permit→contractor + building.parcel_ref all resolve) → **`F2-CASCADE` ✓**.
6. **Collisions + traffic adapters** (RoadSegment + `affects`) → `F2-MOBILITY` ✓.
7. **Minimal Resource stub** (one eVTOL + one inspection crew, `[Simulated]`) → `F2-RESOURCE` ✓.
8. **311 adapter** (breadth; not gated but expected).

After step 7, `run_harness` should return **exit 0**. Snapshot that green state (Rule 9).

---

## 9. Conventions & guardrails

- Use the Pydantic models as the only way to construct entities/edges; never emit hand-built dicts that bypass validation.
- Run the harness after every adapter; treat a non-zero exit as a failing build. Wire it as: `sys.exit(run_harness(entities, edges).exit_code)`.
- Label outputs/datasets with claim labels: real harvested data is `[Implemented]`; the Resource stub and any synthetic fill is `[Simulated]`; the adapter mapping itself is the `[Adapter]` layer.
- Ground every field in a real source field. If a value isn't in the data, it's `None`, not a guess (Rule 3).
- Keep adapters pure/idempotent (same rows → same canonical output) so green states are reproducible.

---

## 10. Open decisions for the human (flag, don't assume)

1. **Building footprints now or later?** v1 uses lot centroids (point). Pulling the NYC Building Footprints dataset (real polygons, by BIN) is a Track-B upgrade — confirm if wanted now.
2. **Full citywide load vs. a Flow-2 neighbourhood slice first?** Recommend resolving a **single neighbourhood** end-to-end first (fast harness loop, proves the cascade), then scaling the harvest. MapPLUTO bulk GDB vs Socrata API pagination is the load-method choice.
3. **Party identity for unlicensed actors** — `name_hash` collision policy (how aggressively to merge similar names) is a confidence/precision tradeoff worth a human call.
4. **311 category mapping** — which 311 `complaint_type`s count as `incident` vs `request` (hazards vs service asks). A small lookup table; confirm the cut.

---

## Addendum A — PLUTO/MapPLUTO, corrected against the official 25v4 (Jan 2026) data dictionary

*Source: the official PLUTO Data Dictionary (25v4, January 2026) + README, now in hand. The bulk PLUTO + MapPLUTO files have been downloaded from DCP. **This addendum supersedes the field names in §6.1 and resolves the load-method decision in §10.2.***

**1. Load method (resolves §10.2).** Use the **downloaded bulk MapPLUTO geofile** (shapefile / File GDB), read with **geopandas** — not the Socrata API. The separate non-geographic **"PLUTO Only" table** carries lots with no polygon (point 5 below).

**2. Projection.** MapPLUTO polygons are in **NAD83 / NY State Plane Long Island (EPSG:2263, US feet)** — **reproject the geometry to EPSG:4326** before constructing `Geometry`. The **`Latitude` / `Longitude` fields are already WGS 84**, so use them directly for the guaranteed `point` (no reprojection needed for the point). *Confirm the shapefile `.prj` before trusting 2263.*

**3. Corrected field names for §6.1 (DCP CamelCase).**

| canonical target | PLUTO/MapPLUTO field |
|---|---|
| Parcel id (`id_system=bbl`) | `BBL` (also `Borough` / `Block` / `Lot`, `BoroCode`) |
| `geometry` (MultiPolygon) | GeoDataFrame `.geometry` — reproject 2263 → 4326 |
| `point` (always present) | `Latitude`, `Longitude` (WGS 84); `XCoord`/`YCoord` are state-plane feet |
| `core.land_use` | `LandUse` |
| `core.zoning[]` | `ZoneDist1`..`ZoneDist4` (+ `Overlay1-2`, `SPDist1-3`) |
| `core.lot_area_sqft` | `LotArea` |
| `core.address` | `Address` |
| Building `building_class` | `BldgClass` |
| Building `num_floors` | `NumFloors` |
| Building `year_built` | `YearBuilt` |
| Building `units_residential` | `UnitsRes` |
| Building `units_total` | `UnitsTotal` |
| Building floor area | `BldgArea` (+ `ComArea`, `ResArea`, `OfficeArea`, …) |
| Party(owner) | `OwnerName`, `OwnerType` |
| `ext['nyc.*']` | `CD`, `Council`, `ZipCode`, `PolicePrct`, `BuiltFAR`, `AssessTot`, `Landmark`, etc. |

**4. No BIN in PLUTO — confirmed.** PLUTO is **lot-level (BBL); it has no BIN field** (it only uses BIN *internally* to compute `NumBldgs`). Consequences for the resolver:
- Building's **BIN comes from the DOB adapters**, not PLUTO. Parcel↔Building remains a **BBL link**.
- **PLUTO's building attributes are lot-aggregate, not per-building.** Carry **`NumBldgs`**; when `NumBldgs > 1`, the lot has multiple buildings and PLUTO's `BldgClass`/`NumFloors`/etc. are an approximation for any single BIN. Attach those at the **Parcel** level; let the per-BIN **Building** entity (from DOB) hold building-specific data.

**5. "PLUTO Only" lots have no polygon.** Some lots — notably condos without an assigned billing BBL — are **not mapped** in MapPLUTO. For these, `geometry` falls back to the **`point`** (Lat/Long); they still produce a valid Parcel (the harness `G-GEO` gate only requires a point). Source them from the PLUTO Only table.

**6. Condos: one record per complex.** PLUTO has **one record per condominium *complex*** (the billing BBL, with `CondoNo`), **not per unit**. For v1, a condo complex = **one Parcel** (Unit is reserved — do not explode units).

**7. `APPBBL` (Apportionment BBL) for the resolver.** When lots are merged/apportioned, BBL changes over time; **`APPBBL` holds the prior BBL.** Use it to reconcile a **DOB permit (or older record) that cites a now-superseded BBL** to the current Parcel — a historical-match case (method `derived_key`, slightly reduced confidence, with `derivation="matched via APPBBL"`).

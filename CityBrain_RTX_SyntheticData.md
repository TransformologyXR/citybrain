# CityBrain RTX — Synthetic Data Stream

*NVIDIA Urban AI demonstration · Stream B deep dive*
*Status: DRAFT v0.1 — for review. Companion docs: Vision · Architecture · Roadmap. Companion data files (place alongside this doc in the source-of-truth folder): `citybrain_open_data_manifest.csv`, `no_key_harvest_queue.csv`, `manual_api_registration_register.csv`, `citybrain_data_harvest_manifest.xlsx`, `harvest_run_summary.json`.*

> This doc is the methodology and status layer for the data factory. **The manifest files are the source of truth for the dataset catalog** — 102 candidate sources across 8 donor cities + global layers; this doc explains how they're used, validated and turned into the brain's ground truth. Don't transcribe manifest rows into prose elsewhere — point back here and to the CSVs.

---

## 1. Core principle

**Don't invent distributions — transplant real ones.** Harvest rich open data from cities that publish it, then re-anchor those real patterns onto Dubai geometry and the canonical entity schema (full thesis in Vision §8; spine placement in Architecture §7). This doc is the *how*: the donor catalog, the generation stack, the validation harness, and the acquisition plan.

---

## 2. Data status legend

A second taxonomy, specific to data (distinct from the [Implemented]/[Simulated]/[Adapter]/[Planned] capability labels in the Architecture doc):

| Symbol | Meaning |
|--------|---------|
| ✅ | Harvested — real sample secured and on disk |
| 🔑 | Real, but needs registration / API key |
| ✋ | Real, but needs manual export (no stable API) |
| 🐛 | Real, blocked by a harvester bug — fixable, no key needed |
| 🔍 | In the manifest, not yet attempted this run |
| 🧪 | Synthetic only — no real-world donor; generated or calibrated |

---

## 3. Donor city catalog — status snapshot

Counts and roles per the manifest (`citybrain_open_data_manifest.csv`, 102 rows); see the CSV for exact dataset names, IDs and URLs.

| City | Role | Manifest rows | Confirmed this run | Status |
|------|------|---------------|---------------------|--------|
| **NYC** | Master operational donor | 18 | PLUTO, 311 (×2 archives), DOB filings/permits/complaints, traffic speeds/volumes, collisions, EMS + fire dispatch, LL84 energy, permitted events, restaurant inspections | ✅ 14/16 sampled; 3D Building Model + DEM are 🐛 (file-resource fix needed) |
| **Chicago** | Civic sensor + municipal ops | 10 | 311, building permits, building violations, energy benchmarking, traffic crashes, food inspections | ✅ 6/6 sampled clean. Array of Things + air sensors 🔍 not yet sampled |
| **Dubai** | Real-estate-gov / golden-path scenario | ~10 | — | ✋ all manual export (DLD, DM, Bayanat, Police) — see §9 |
| **London** | UK resilience / emergency / energy | 7 | LFB incident + mobilisation records, smart-meter consumption | 🐛 ×3 (API-path issue, page-scrape fallback recommended); TfL 🔑; LAQN 🔍 |
| **Helsinki** | Semantic 3D twin donor | 7 | 3D city model, traffic volumes | 🐛 ×2 (HRI API mounted under `/data/`, base path fix needed) |
| **Amsterdam / Netherlands** | 3D + traffic + kerbside | ~8 | — | 🔍 not yet sampled (3DBAG, PDOK/BAG, NDW, parking WFS) |
| **Singapore** | Real-time API + camera "eyes" | 7 | — | 🔑 LTA DataMall, OneMap; data.gov.sg likely no-key for testing |
| **Melbourne** | Crowd / pedestrian / kerbside | ~9 | Pedestrian counts, parking bay sensors, parking bays (attempted) | 🐛 ×3 (OpenDataSoft page-size cap — use `/exports/csv`, not `/records`) |
| **Global / base layers** | Cross-city foundation | 21 | — (see §4) | Mixed — see below |

**Read-through:** the golden path's primary donor (NYC) is essentially de-risked. The three secondary-flow donor classes that failed (London, Helsinki, Melbourne) all failed for narrow, diagnosed, non-credential reasons — none of them need registration to fix.

---

## 4. Cross-city base layers (Global, 21 manifest rows)

| Layer | Source | Status | Use |
|-------|--------|--------|-----|
| Road/building/POI geometry | OpenStreetMap (Geofabrik/HOT) | 🔍 no key, manual AOI extract | SUMO networks, base city graph |
| Stable cross-source IDs | Overture Maps | 🔍 no key, filter by bounding box | Canonical-ID anchor strategy |
| Building footprints/heights | Microsoft Global ML Building Footprints | 🔍 no key | Fill geometry gaps for the twin |
| Population priors | WorldPop gridded population | 🔍 no key | Demand/occupancy/evacuation priors |
| Weather reanalysis | ERA5 (Copernicus CDS) | 🔑 needs CDS token | Flood/heat stress scenarios (Flow 5) |
| Power system time series | Open Power System Data | 🐛 local script bug (`.part` file collision) | Energy-Water Stress Lab pack |
| Synthetic generation tooling | NVIDIA Omniverse Replicator | install, no dataset key | Procedural scene + label generation |
| Vision benchmark sets | AI City Challenge / Waymo / BDD100K / CityFlow | 🔑/✋ licence acceptance | Reference only — not redistributed in the demo |

---

## 5. The generation stack

Four parallel lanes converge into one gate before anything reaches the spine:

![Generation stack and validation gate](CityBrain_RTX_diagram_genstack.svg)

*Figure — donor data feeds four generation lanes (structure, dynamics, events & documents, vision); all four converge into the validation harness; only validated output reaches ingestion (L1).*

| Lane | What it produces | Primary inputs | Claim label (target) |
|------|-------------------|-----------------|----------------------|
| **Structure** | The static city: parcels, buildings, roads | OSM, Overture, 3DBAG, MS footprints, donor-city geometry | [Simulated] — real geometry, re-anchored |
| **Dynamics** | Time-varying behaviour: traffic, power, water | SUMO / pandapower / EPANET, **calibrated to harvested real distributions** (NYC traffic speeds, donor smart-meter curves) | [Simulated] |
| **Events & documents** | Permits, complaints, inspections, dispatch records | Schema-grounded LLM generation, seeded by real donor-record *shapes* (field distributions, not literal content) | [Simulated] |
| **Vision** | Camera/sensor frames for the perception layer | Cosmos (Transfer/Predict/Reason) over the OpenUSD scene | [Simulated] |

None of these lanes "invent" a distribution from nothing — each is anchored to a harvested real dataset's shape, even where the specific record is synthetic.

---

## 6. Schema normalization & re-anchoring

1. **Map** each donor dataset's fields to the CityBrain canonical schema (parcel, building, unit, permit, inspection, asset, road segment, sensor, event — per Architecture §1–2).
2. **Re-anchor** the donor's *statistical behaviour* (not its literal geography) onto Dubai's real geometry and entity set — e.g., NYC's permit-to-inspection time distribution informs Dubai's synthetic permit cartridge, but the parcels themselves are Dubai's.
3. **Assign provenance** at the field level: every synthetic record carries which donor pattern it was drawn from, so the demo can show its homework if asked.
4. **Freeze schema v1 early** (Roadmap §6) — this blocks the registry, the graph, and every adapter in this stream.

---

## 7. Validation harness (the mandatory gate)

Three checks, all automated, all must pass before data reaches ingestion:

1. **Distribution checks vs real.** Synthetic traffic-speed, permit-timing, or pedestrian-count distributions are compared against the donor city's real distribution (e.g., a Kolmogorov–Smirnov or simple quantile comparison) — flags anything that drifted into "invented" territory.
2. **Constraint & referential-consistency checks.** Every permit references a real parcel; every inspection references a real permit; every event timestamp is causally ordered; no orphaned foreign keys.
3. **Downstream "does the brain answer correctly" check.** A fixed set of test queries (e.g., "what's the status of area X") is run against the populated graph, and the answer is checked against the known-correct synthetic ground truth — this is the check that actually matters for the demo, because it tests the *brain*, not just the data.

This harness is built in Phase 0 of the master Roadmap (Rule 7: build the eval harness before the code it judges) and gates every dataset, real or synthetic, before it's trusted.

---

## 8. Cartridge data map

Which donor data feeds which flow (Vision §6–7). 🔍/🔑/✋ items are open actions, not blockers for flows that don't need them yet.

| Flow | Primary real data | Status | Synthetic fill |
|------|--------------------|--------|-----------------|
| 1 — Situational status | NYC PLUTO ✅ + Dubai DLD ✋ | partial | Graph/registry synthetic overlay |
| 2 — **Golden path** (construction cascade) | NYC PLUTO, DOB permits/filings/complaints, traffic speeds ✅ + Dubai DM/DLD ✋ | NYC side ready; Dubai pending manual export | Vision events (Cosmos), risk/impact prediction |
| 3 — Resilient city (fire/road/air) | London LFB incident + mobilisation 🐛, TfL 🔑, LAQN 🔍 | needs the 3 fixes + a TfL key | Cross-event cascade simulation |
| 4 — Crowd surge | Melbourne pedestrian + parking 🐛, Singapore LTA images 🔑, GTFS-RT 🔍 | needs OpenDataSoft export-endpoint fix + LTA key | Crowd-cascade prediction |
| 5 — Flood / asset cascade | NYC DEM 🐛, ERA5 🔑, London flood data 🔍 | needs file-link fix + CDS token | EPANET 🧪, Cosmos flood frames 🧪 |
| 6 — Oil-rig shutdown | — (domain knowledge, not open data) | n/a | Fully 🧪 — schema + script from founder's Petrotechnics background |
| 7 — Civic service fusion | Chicago 311, violations, energy benchmarking ✅ | ready | Array of Things / air sensors 🔍 to enrich later |

**Read-through:** Flow 2 (golden path) and Flow 7 are the closest to fully real-data-ready. Flow 6 needs no public data at all. Flows 3–5 each need exactly one concrete unblock (a harvester fix or a key) before their donor data is live.

---

## 9. Acquisition waves (Stream B, mapped to the master Roadmap)

| Wave | Focus | Maps to Roadmap | Gate |
|------|-------|------------------|------|
| 1 | Open no-key samples (NYC, Chicago Socrata; Melbourne OpenDataSoft; London/HRI metadata) | Phase 0 | ≥20 datasets have metadata/sample/tested URL — **essentially met (19/31)** |
| 2 | Geometry/twin anchors (NYC 3D/PLUTO, Helsinki 3D/HRI, 3DBAG/PDOK, OSM/Overture extracts) | Phase 1–2 | A visible asset shares one canonical ID across source, graph and twin |
| 3 | Operational dynamics (traffic, EMS/fire, 311, permits/violations, pedestrian/parking, energy/water) | Phase 1, 3 | Each stream passes the distribution + consistency checks (§7) |
| 4 | Manual/key sources (TfL, LTA, OneMap, Street Manager, ERA5/CDS, AirNow/EIA) | Ongoing, parallel from Day 0 | Credentials stored; sample pull documented per source |
| 5 | NVIDIA synthetic sensor reality (Replicator/Cosmos frames, camera placements, labels) | Phase 2 | Every frame/event maps to sensor ID, entity ID, scenario ID and a ground-truth manifest |

---

## 10. Access register — what to actually go register (P0 first)

From `manual_api_registration_register.csv`, ranked:

1. **TfL API app_key** — register, store as `TFL_APP_KEY` (unblocks Flow 3).
2. **LTA DataMall key** — submit Request for API Access, store `AccountKey` (unblocks Flow 4's vision "eyes").
3. **Dubai manual export** (DLD / DM / Bayanat / Police) — no key, but manual download/verification — **this is the actual golden-path blocker**, not a credential task.
4. *(P1/P2, not blocking any flow yet)* OneMap token, Street Manager registration, Copernicus CDS account (ERA5), EIA key, AirNow key.

---

## 11. Known harvester bugs (status log for build agents)

Logged here so whichever agent picks this up has the diagnosis already done — no re-investigation needed:

- **NYC 3D Building Model / DEM (403):** these Socrata IDs are file/attachment resources, not queryable tables. Fetch the dataset's attachment/download link directly instead of the SODA `$limit` CSV export.
- **London LFB ×2 + smart meter (404):** dataset slugs are correct (verified live); the CKAN action-API path used doesn't resolve on the current London Datastore platform. Fall back to scraping the published CSV/zip link from the dataset page.
- **Helsinki ×2 (404):** HRI's CKAN install is mounted under `/data/` — the API base must be `hri.fi/data/api/3/action/...`, not `hri.fi/api/3/action/...`.
- **Melbourne ×3 (400):** OpenDataSoft's v2.1 `records` endpoint caps page size (~100); requesting `limit=100000` exceeds it. Use the `/exports/csv` endpoint instead, which streams the full file with no page cap.
- **Open Power System Data (Windows file error):** stale `.part` file from a prior run; clear partials before retry or write to a unique temp path.

None of these require credentials. All are narrow, fixable bugs.

---

## 12. Next

- Patch the harvester per §11 (whenever picked up — not currently blocking).
- Execute the Dubai manual export (§10.3) — the real golden-path unblock.
- Wire Wave 1's confirmed NYC/Chicago data into the registry once schema v1 freezes (Roadmap Phase 0–1).
- Feed this doc's cartridge map (§8) into **Mission Control** as the live per-flow data-readiness view.

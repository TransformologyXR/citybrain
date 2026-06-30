# TXR City Brain — Current Certified State

**Document 1 of 4** · *Companion docs: 02 Application Snapshot DoD · 03 Platform v1 DoD · 04 Full Vision Completion Map*

**Status date:** 2026-06-27
**Document purpose:** Single source of truth for what is *actually* green, verifiable, and pinned today. Nothing aspirational. Nothing in-progress. Only what has passed its acceptance gate and been snapshotted.

**How to maintain this document:** This doc is updated whenever a milestone formally passes its acceptance gate and is snapshotted. Items that are in-progress, deferred, or planned do NOT appear here — they live in docs 02–04. If an item is removed from this doc (e.g., a regression breaks a gate), the removal is explicit and dated.

**Claim labels used throughout:**
- `[I]` Implemented — runnable, gated, snapshotted on real data
- `[A]` NVIDIA-compatible Adapter — works on top of a real NVIDIA component (NIM, RAPIDS, cuGraph, cuOpt)
- `[S]` Simulated with generated or illustrative data — honestly labelled as such in the artifact
- `[P]` Planned — *does not appear in this document*

---

## 1. Architectural baseline

A city-scale governed data → graph → query → optimisation → web-operating-surface path is proven for NYC construction-compliance, with provenance and claim-boundary discipline enforced end-to-end. London is an accepted second-city core for Flow 2: identity backbone, planning corpus, Local Plan semantics, a certified (if partial) enforcement-identity slice, live governed wrapper, live face layer, and dual hero scenarios are reconciled into the accepted London line. NYC Flow 3 and Chicago Flow 1 + Flow 7 now prove the next slotting model: accepted city cores can carry flow sub-cartridges without rebuilding the city from zero.

The system does **not yet** exercise the complete nine-layer architecture because L4 (live event fabric), L6 (twin + simulators), L7 (runtime perception), and parts of L8 (cinematic twin + persona layer) remain open. Those are tracked in docs 02–04.

---

## 2. Hardware — all four machines live

| Machine | Role | Status |
|---|---|---|
| DGX Spark (Blackwell, ARM64, 192.168.1.103) | Action core — NIM Llama-3.1-8B + NeMo Agent Toolkit | `[I]` live · :8000 healthy |
| RTX 3090 (Ampere, x86, txr-3090, 192.168.1.148) | RAPIDS / cuGraph / cuOpt | `[I]` live · Ubuntu, Docker, NVIDIA Container Toolkit, RAPIDS 26.06, cuOpt 26.6.0 all verified |
| RTX 4070 (Ada, x86, txr-4070, 192.168.1.48) | Face layer — Caddy / Node / MapLibre — briefing / trace / map / routes | `[I]` live · all endpoints serving real data |
| RTX 5090 laptop (Blackwell, Windows) | Controller + Dubai Creek USD twin | `[I]` live · 5090 SSHes to all three GPU boxes; 3090→4070 direct SSH denied, transfers routed through laptop bridge with hash verification |

**Deliberately deferred on the 4070:** DeepStream / Triton / Metropolis / VSS — no perception input exists yet.

---

## 3. Spine layers — what is certified

### L1 · Ingestion & adapters — strong for NYC, accepted London core

| Adapter | Claim | Evidence |
|---|---|---|
| NYC PLUTO / MapPLUTO (parcels) | `[I]` | Full citywide ingest; CamelCase field handling, EPSG:2263→4326 reproject for polygons, APPBBL reconciliation, BBL preserved as zero-padded string |
| NYC DOB Permit Issuance | `[I]` | 17 hero-area Permit entities, exact-key identity |
| NYC DOB NOW Permits | `[I]` | 44 hero-area Permit entities (filings vs issuance honestly disjoint) |
| NYC DOB Complaints | `[I]` | 119-code taxonomy via `dob_complaint_categories.py` (neutral module, generic helper) |
| NYC Building Footprints | `[I]` | 1,012,067 polygons with `roof_height` / `ground_elevation`, BIN string-preserved |
| NYC 11-dataset harvest | `[I]` | 5M+ rows total, prep v0.2 string-safe Parquet |
| RAPIDS cuDF GPU tabular load | `[I]` | Real parquet read on 3090, 49,465 × 271 LL84 dataset, GPU memory verified via `nvidia-smi` |
| London UPRN (parcel) — serious scale | `[I]` | 5.31M UPRN identity, full London coverage (LON·D9 chain) |
| London TOID (building) — serious scale | `[I]` | 2.30M TOID identity (LON·D9 chain) |
| London USRN (road segment) — serious scale | `[I]` | 69.7K USRN identity (LON·D9 chain) |
| London identity edges | `[I]` | 10.61M identity edges, accepted graph 7,734,960 nodes / 10,664,896 edges, 0 missing endpoints |
| London LIDS crosswalks | `[I]` | UPRN-Street-USRN, UPRN-TopographicArea-TOID, UPRN-RoadLink-TOID |
| London PLD planning permissions — citywide | `[I]` | 58,867 normalized PLD applications, all 33 boroughs |
| London official PLD API UPRN recovery | `[I]` | 57,796 exact matches, 53,753 PLD→UPRN edges — no fuzzy joins |
| London planning-context enrichment (LON·D10) | `[I]` *context only* | 186,180 context nodes / 232,101 context edges / 53,751 PLD-with-context / 32–33 boroughs — context, NOT a legal planning determination |
| London Local Plan semantic certification (LON·D10B) | `[I]` *partial certification* | 444 of 1,139 candidate layers certified, 695 manual-review; 55,469 nodes / 168,116 edges; 36,352 PLD + 27,551 UPRN with Local Plan context; 33/33 boroughs |
| London TOID geometry (LON·D11A) | `[I]` *generalised-location point* | 40,803 / 40,804 accepted TOIDs matched via OS Open TOID; **point geometry only — not footprint polygons**, which need licensed OS MasterMap |
| London EV charging context (LON·D10EV) | `[I]` *scope-limited* | 156 official rapid-charging sites (London Datastore GeoPackage), 31/33 boroughs, 1,615 context edges — rapid-charging only, no real-time availability |
| London enforcement / building-control | `[I]` *partial identity recovery* | LON·D6B2: 532 official Havering enforcement events, all SHA-256 documented. LON·D6B3/D6B4: 190 certified identity edges via exact PLD reference (148 official API exact matches, 104/106 OpenUPRN-verified). 5,181 address/postcode/fuzzy candidates correctly rejected, kept candidate-only — most Havering events remain unjoined or candidate-only |
| London deterministic NeMo wrapper (LON·D12) | `[I]` | 1 public tool `citybrain_london_query`, 8/8 sample requests, grounding + negative-request + no-overclaim all pass |
| London live NIM narration (LON·D12b/D13c) | `[I]` | Live NIM answered the London sample set, grounding passed; re-smoked clean at D13c |
| London face-layer cartridge (LON·D11/D11C) | `[I]` | `/london` and `/api/london/*` live on the 4070, 10/10 endpoint attempts passed (re-smoked at D13c) |
| London composite accepted snapshot (LON·D13/D13b/D13c) | `[I]` | Single reconciled source of truth; live NIM and live face both re-smoked against the final state, not just file-merged |

**Not in this document (tracked elsewhere):** Overture base-layer adapter, MS Building Footprints global adapter, WorldPop, ERA5, GTFS, BIM/IFC, document-text adapter, mobility adapters. See doc 04.

### L2 · Canonical entity registry — schema v1 complete and proven, cross-city ontology v2 not yet started

**Schema v1 (frozen):**
- 8 core entities: Parcel, Building, Permit, Party, Inspection, RoadSegment, Event, Resource
- 5 reserved entities (in schema, not yet activated): Unit, Development, Sensor, InfrastructureAsset, TransitNode
- Identity triad on every entity: `canonical_id` + `provenance[]` + `confidence`
- ID format: `{entity_type}:{country}-{city}:{id_system}:{native_id}` (e.g., `building:us-nyc:bin:1026676`, `parcel:uk-london:uprn:{uprn}`)
- Party-with-role (role on edge)
- Event two-level taxonomy (category enum + open type)
- Resolution-via-edges carrying own confidence

**Files:**
- `txr_citybrain_schema_v1.py` (Pydantic v2, pinned `pydantic==2.13.4`)
- `txr_citybrain_schema_v1_schema.json`
- ERD: `TXRCityBrain_Schema_ERD.svg`

**Identity coverage by city:**
- NYC: BBL (Parcel) + BIN (Building) — proven end-to-end on hero cascade + citywide
- London: UPRN (Parcel) + TOID (Building) + USRN (RoadSegment) — proven at full London scale (5.31M UPRN / 2.30M TOID / 69.7K USRN), accepted Flow 2 city core

**Honest nuances pinned in evidence:**
- London exposed an `on_street` vocabulary compatibility need; addressed via compatibility-harness treatment in LON·D4–D8, *not* an unchanged binary A2 pass. This is honest evidence that the model is extensible; it also means a cross-city ontology v2 reconciliation is open work (tracked in doc 03).
- UPRN-as-Parcel is a bounded design choice; a durable distinction among `addressable location / parcel / building / unit` is open work.
- Authoritative jurisdictional identifiers (BBL, BIN, UPRN, TOID) are preserved as canonical primaries; Overture / cross-source IDs would be added as **aliases** in a future ontology v2, never replacements.

### L3 · Multiplex semantic graph (cuGraph) — strong for NYC, accepted London core

**NYC citywide graph (a4·D3b):**
- 27,997 active blocks projected
- 7,330,796 nodes, 9,637,245 edges
- 440,740 components (largest 5,903,970)
- 5,347 MB peak GPU memory on 3090
- 3.77s GPU graph operation time (550s total wall, I/O bound)
- Per-borough projections also pinned: Manhattan 1,936 blks / 1.8M nodes / 3.0M edges; Bronx 2,985 / 787K / 961K; Brooklyn 7,492 / 2.07M / 2.53M; Queens 11,797 / 2.17M / 2.49M; Staten Island 3,787 / 572K / 634K
- Byte-stable regression: GPU output matches CPU baseline from a4·D3a exactly
- Round-trip portable: laptop read of Staten Island subset, harness pass on local copy

**A4 gate set (all green on citywide):**
- A4-UNIQUE, A4-VOCAB (the fork-catcher), A4-NODE-FID, A4-EDGE-FID, A4-CONF, A4-TRAVERSAL
- DISTRICT-cut gate
- Drift test (TaxLot/HAS_PERMIT fork + dropped confidence + raw node) fires 5 gates red as expected

**Hero cascade green at v3:**
- complaint `1366080` (category 91, critical, entered 2014-02-21)
- → building `BIN 1026676` (via exact_bin, ~0.95 confidence)
- → permit `121912591` (issued 2014-02-07, 14 days before complaint = work-caused)
- → contractor `S&E BRIDGE & SCAFFOLD LLC` (GC-0037441, exact-license 0.95 confidence)
- → parcel `BBL 1010607502` = 425 WEST 50 STREET, Hell's Kitchen, R8 zoning (reached transitively via existing `has_building` edge — never via exact_bbl, complaints carry no BBL)

**Honest nuances pinned:**
- Graph is a faithful *projection* (read-model) of canonical entities, not a second schema. Reuses canonical vocabulary; never invents TaxLot or HAS_PERMIT. The drift test catches forks.
- "61 exact-key Permit entities" wording is honest (44 NOW + 17 Issuance, zero overlap = disjoint lifecycle windows in harvest), never overstated as "61 unique jobs."
- 47 high-license + 64 low-name-hash parties (58% soft, surfaced in output).

**Implementation note:** at million-row scale, the harness uses a vectorized Parquet + gate path rather than Pydantic JSON. Same invariants gated; implementation adapted to scale.

**London graph projection (LON·D7 through D13c):** `[I]` done. Accepted graph: 7,734,960 nodes / 10,664,896 edges, 0 missing endpoints. The same a2 harness pattern (with documented compatibility-harness treatment for `on_street`, see L2 above) gates this graph the same way it gates NYC's. LON-HERO adds the dual accepted hero scenarios; future London work should mount as `LON-F*X-*` sub-cartridges unless a scout proves a missing core dependency.

### L4 · Observation / event fabric — thin

What exists today: temporally-stamped historical records (DOB complaints, permits) treated as Events in the schema. This is *not* a living event fabric; it is historical evidence the system reasons over.

What is **not** in this document (tracked in doc 03):
- Append/replay event stream
- Event-time vs processing-time semantics
- Current-state materialization
- Continuous signals (traffic, meters, air quality)
- Late/out-of-order handling
- Replayable scenario packs

### L5 · Cognition engine — Query mode strong; Incident/Plan/forward-dynamics/inverse-dynamics/monitor not built

| Capability | Claim | Evidence |
|---|---|---|
| Deterministic operator query (a5·D1) | `[I]` | Evidence-backed answer with confidence + provenance |
| Spark portability pack (a5·D2) | `[I]` | Clean-room run on Spark with NIM contract + NeMo contract |
| Live Spark/NIM/NeMo hero smoke (a5·D3) | `[I]` | NIM narrates over real evidence; deterministic facts unchanged |
| EvidenceBundle v1 + grounded narration gate (a5·D4a) | `[I]` | Briefing facts ⊆ EvidenceBundle (programmatic); 2nd-subject proof on BBL 1010600029 |
| Request validator + complete trace (a5·D4b) | `[I]` | Bad query rejected with reason; full reasoning trace recoverable |
| NeMo wrapper exposes single tool (a5·D5) | `[I]` | NeMo calls only `citybrain_oracle_core`; no low-level bypass possible |
| Live NeMo/NIM replay through governed wrapper (a5·D6) | `[I]` | Grounded on both subjects; negative request rejected before deterministic execution |
| Narration surface — prose briefing (a5·D6b) | `[I]` | Subset-grounded, anti-echo, min-coverage, subject-isolated; closes the AP-Physics-style echo trapdoor |
| Citywide precomputed briefing/trace (a5·D7) | `[I]` | All 27,997 active blocks briefable; non-hero leakage scan = 0 |
| Live Spark citywide query on demand (a5·D7b) | `[I]` | Any active block; hero parity byte-aligned vs precomputed (1461 nodes / 2139 edges / 711 complaints / 11 critical / 1175 permits) |

**Governance pattern (load-bearing):** Code computes every number. The model only narrates over the deterministic output. Two outputs (structured evidence + prose narration), two gates (exact-match for evidence, subset-grounding + anti-echo + min-coverage for narration). The gates work *against* each other so the model has to genuinely narrate rather than echo evidence verbatim. This is the project's central architectural claim and it holds end-to-end.

**Not in this document:** the full 9-stage orchestration (RECALL→…→COMPLETE), Incident mode, Plan mode, forward dynamics, inverse dynamics, monitor loop. These are deliberate non-builds (the lean narrator was the correct call for the current scope) and they appear in doc 03.

### L6 · Simulation & optimisation — one cuOpt use case proven; no twin, no domain simulators, no rollouts

| Capability | Claim | Evidence |
|---|---|---|
| cuOpt operational review optimizer (a6·D1) | `[I]` | 120 candidates extracted from citywide a4·D3b graph → 60 route candidates → 33 assigned across 3 teams (Manhattan 12, Bronx 11, Brooklyn-Queens 10) covering all 5 boroughs; 27 dropped honestly by capacity/shift constraints; 60 held by route cap; CPU baseline validated; operator-safe language enforced (review, not enforce) |

**Not in this document:** Omniverse / OpenUSD city twin (Dubai Creek scene exists but for a different city and is unwired to NYC graph), SUMO, pandapower, EPANET, Cosmos rollouts, asset-dependency edges, additional cuOpt problem families. See docs 03 and 04.

### L7 · Perception / vision — runtime absent

What exists today:
- Illustrative video assets (5 CC0 clips from Pexels/Pixabay, labelled `[Illustrative]` with explicit non-evidence boundary, attached to hero cascade in `/briefing`)
- A proposed PPE adapter contract (off-the-shelf YOLO/PPE on 4070 via Triton)
- Hardware readiness on 4070
- A sensible separation between perception (eyes) and judgment (brain)

What does **not** exist at runtime:
- Model inference
- Tracking
- Zone logic
- Event JSON emission
- Evidence-clip generation
- Canonical event resolution from vision

Tracked in docs 02 and 03.

### L8 · Experience & personas — web face strong; cinematic twin + persona layer absent

| Surface | Claim | Evidence |
|---|---|---|
| Citywide map with LOD (a8·D2) | `[I]` | Borough → block → node zoom levels; viewport-bounded (≤5K features); heatmap by critical-complaint count; block-key search; on http://192.168.1.48:8080/map/ |
| Real building polygons on map (a3·D2) | `[I]` | 1,012,067 polygons with heights; hero building visible as MultiPolygon; 94.88% all-Buildings polygonized, 99.91% footprint→active-Building coverage (honest dual denominators) |
| Route overlay from cuOpt (a8·D3) | `[I]` | Routes + sites rendered; counts match a6·D1 output exactly (120/60/33/27/60) |
| why_selected plain-English tooltips (a8·D3b) | `[I]` | Honest wording, e.g. "Selected because block 3-03673 has 204 critical complaints, 667 complaints, 122 permits in the current harvested dataset" — boundary statement carried into UI copy |
| Hero clip attachment (a8·D3b) | `[Illustrative]` | `clip_01_primary.mp4` (Pexels / Waleed Talat, 26s, 11.77MB) served at /clips; `/briefing` shows hero-cascade clip panel with `[Illustrative · Pexels]` label and explicit non-evidence boundary |
| Citywide precomputed `/briefing` (a5·D7) | `[I]` | Any active block resolvable; 404 with honest message on invalid; hover-to-evidence highlighting |
| Live `/briefing?block=X&mode=live` (a5·D7b) | `[I]` | Spark-served on demand; hero parity verified |
| London face layer `/london` + `/api/london/*` (LON·D11/D11C) | `[I]` | Live on the 4070; generic shell replaced; 10/10 endpoint attempts passed; re-smoked clean at D13c |

**Not in this document:** Omniverse 3D control room, BIN-tagged USD scene with click-through to graph, four SOUL personas, multi-agent trace panel as polished product feature, approval UI, HITL gates. See docs 02 and 03.

### L9 · Governance — strong on what is gated; consequential-action layer not yet exercised

**What is gated today:**
- Provenance on every entity (which source, when, how derived)
- Confidence on every entity and every edge
- Claim-boundary labels (`[I]`/`[A]`/`[S]`/`[P]`) on every claim surfaced
- Grounded narration (subset-grounded, anti-echo, min-coverage, subject-isolated)
- Negative tests (invalid queries rejected before deterministic execution)
- Operator-safe wording (review, not enforce; recommend, not act)
- No-mutation gates (accepted artifacts never mutated by downstream tasks)
- Drift gates (5 different fork patterns fire as expected on intentional break)
- Traceability (full reasoning trace recoverable on every query)
- NeMo Guardrails active in the wrapper (single-tool exposure)

**Open in governance** (tracked in doc 03):
- Explicit approval object/state
- Approve/reject/modify lifecycle
- Consequential-action policy (does not exist because the system is review-only today)
- Live guardrail gate proving guardrails are active on accepted *and* rejected paths
- Audit log for action proposals
- Monitoring after approved action

---

## 4. Cartridge ledger

| Cartridge | Status |
|---|---|
| Flow 2 — NYC construction-compliance | `[I]` certified deep, citywide |
| Flow 3 — NYC incident / response / affected-context | `[I]` accepted with full-source inputs and stage limitations (F3-NYC-D9FULL); not emergency dispatch, not certified affected-building truth |
| Flow 2 — London city core (second-city proof of same flow, different identity backbone) | `[I]` accepted — full identity + planning + Local Plan + partial enforcement-identity + live wrapper + live face + dual hero scenarios |
| LON-F3X — London resilience / fire-incident context extension | `[I]` accepted through LON-FLOWX-D6; D2 landed bounded LFB incident/mobilisation schemas/samples and hardened joins; review-only, not emergency command, fire dispatch, or certified affected-asset truth |
| LON-F4X — London mobility / environment extension | `[I]` accepted through LON-FLOWX-D6; TfL status/disruption/BikePoint + London Air context landed with join hardening; review-only, not route guarantee, public-order instruction, or health determination |
| LON-F5X — London flood / climate-risk extension | `[I]` accepted through LON-FLOWX-D6; EA flood warnings/stations/areas + London Air/emissions discovery landed with join hardening; risk context only, not utility control or emergency response |
| Flow 1 + Flow 7 — Chicago situational status + civic/sensor fusion | `[I]` accepted as CHI-F1F7-D5 over an expanded, still source-limited public-data base; not operational recommendation, policing, dispatch, enforcement, health, emergency, or public-safety instruction |

**Slotting update:** Treat NYC, London, and Chicago as accepted **city cores**. New flows mount as city-flow sub-cartridges using the `{CITY}-F{FLOW}X-D{DAY}` convention. `LON-F3X`, `LON-F4X`, and `LON-F5X` are now accepted London flow-extension snapshots mounted onto the accepted London core, not fresh London cartridges.

**Honest framing:** London is accepted today as **Flow 2 plus mounted review-context extensions for Flow 3/4/5**. The F3X/F4X/F5X extensions inherit the London core IDs, face/NIM conventions, and limitations, and add their own source ledgers, joins, EvidenceBundles, replay/live proof, hero/freeze package, no-overclaim scan, and accepted D6 snapshot. Singapore Flow 4 remains planned until authenticated live API proof clears. Barcelona is a fresh city-core scout candidate.

**Not in this document:** Singapore Flow 4 accepted proof, Barcelona core, Dubai cartridge, oil & gas cartridge. See docs 03–04 and `TXRCityBrain_CityCore_Subcartridge_Model.md`.

---

## 5. NVIDIA stack coverage — what is genuinely live

| NVIDIA component | Claim | Status |
|---|---|---|
| NIM (model serving — Llama-3.1-8B) | `[I]` | Live on Spark :8000 |
| NeMo Agent Toolkit | `[I]` | Live on Spark; wrapper exposes single oracle tool |
| NeMo Guardrails | `[I]` *partial* | Active in wrapper; **not yet proven by a dedicated live guardrail gate** — see doc 02 |
| RAPIDS cuDF | `[I]` | Live on 3090, real-data probe pinned |
| RAPIDS cuGraph | `[I]` | Citywide projection on 3090, 7.3M nodes / 9.6M edges |
| cuOpt | `[I]` | Live on 3090, image `nvcr.io/nvidia/cuopt/cuopt:26.6.0-cuda12.9-py3.14`, a6·D1 operational use case proven |
| Docker / NGC packaging | `[I]` | All GPU stacks containerized; cuOpt + RAPIDS images pinned by digest |
| Omniverse / OpenUSD | `[S]` *partial* | Dubai Creek USD scene runs @60fps on 5090 — different city, not wired to NYC graph; NYC twin **does not exist** |

**Not in this document** (i.e., not currently live in our build):
- Cosmos Predict/Transfer/Reason
- Metropolis / DeepStream / VSS
- grounding-dino
- NeMo Curator
- cuVS / NeMo Retriever
- Earth-2 / CorrDiff

---

## 6. Honest numbers worth remembering

- "61 exact-key Permit entities" never overstated as "61 jobs"
- 94.88% all-Buildings-polygonized vs 99.91% footprint-coverage (two true numbers, different denominators, both reported)
- complaint → building via exact_bin (~0.95), parcel reached transitively via has_building edge — never via exact_bbl
- 47 high-license + 64 low-name-hash parties (58% soft, surfaced in output)
- All NYC counts qualified as "current harvested dataset" — boundary statement carried into UI tooltip copy
- London identity at full scale: 5.31M UPRN / 2.30M TOID / 69.7K USRN / 10.61M identity edges — accepted graph has 0 missing endpoints
- London PLD official API UPRN recovery: 57,796 exact matches, 53,753 PLD→UPRN edges — zero fuzzy joins
- London enforcement identity: 190 certified edges via exact PLD reference (out of 532 official Havering events) — 5,181 address/postcode/fuzzy candidates correctly rejected and kept candidate-only; most Havering events remain unjoined
- London Local Plan: 444 of 1,139 candidate layers certified, 695 honestly left at manual-review — not all Local Plan context carries the same certification weight
- London TOID geometry is generalised-location **point**, not footprint **polygon** — labelled as such everywhere it surfaces
- D10/D10B are planning-context evidence, never a legal planning determination — stated in every London-facing surface
- DOB severity assignment in `dob_complaint_categories.py` is *our adapter's interpretation*, not DOB's official A–D priority — labelled as such in the module

---

## 7. Files & artifacts (pinned)

**Schema:**
- `txr_citybrain_schema_v1.py`
- `txr_citybrain_schema_v1_schema.json`
- `TXRCityBrain_Schema_ERD.svg`

**Harness & gates:**
- `txr_citybrain_harness.py`
- `txr_citybrain_a4_graph_gate.py`
- `dob_complaint_categories.py` (neutral taxonomy module)

**NYC adapters & flows:**
- `txr_citybrain_nyc_flow2_adapter.py` (legacy hero-era, quarantined, PREFERRED_BBL guards in place)
- `txr_citybrain_a5_dob_enrichment.py`
- `txr_citybrain_a4d2b_district_discovery.py`
- `txr_citybrain_a4d3a_multidistrict_projection.py`
- `txr_citybrain_build_a4_projection.py`
- a4·D3b citywide outputs on 3090: `/data/citybrain/a4d3b_outputs/`
- `snapshot/a4d3b_citywide_v1/`
- `snapshot/nyc_flow2_green_v3.json`

**a5 governed core:**
- `txr_citybrain_a5d4a_evidence_grounding_core.py`
- `txr_citybrain_a5d4b_request_trace_core.py`
- `txr_citybrain_a5d5_nemo_oracle_wrapper.py`
- `txr_citybrain_a5d6_live_nemo_nim_replay.py`
- `txr_citybrain_a5d6b_narration_surface.py`
- `txr_citybrain_a5d7b_spark_live_citywide_query.py`

**a6 cuOpt:**
- `/data/citybrain/a6d1_cuopt_review_optimizer/`
- `A6D1_HARNESS_REPORT.json`, `A6D1_OPERATOR_REVIEW_PLAN.md`, `A6D1_OPTIMIZATION_RESULT.json`
- `face_layer_export/a6d1_review_routes.json`, `face_layer_export/a6d1_review_sites.geojson`

**a8 face layer (4070):**
- `/srv/citybrain/current/` (Caddy deploy)
- `/data/citybrain/from_3090/a8d3_route_overlay_v1/`
- `/data/citybrain/from_dev/citywide_briefings_v1/`
- Endpoints: `/map/`, `/briefing/`, `/trace/`, `/api/routes/summary`, `/status.json`

**a3·D2 footprints:**
- `outputs/a3d2_footprints_geometry_v1/`
- 1,012,067 polygons, byte-stable a4·D3b regression preserved

**London:**
- `LON_D3_probe_review_v0_2.zip` (source reachability)
- LON·D4–D13c snapshots pinned (identity → planning → context → Local Plan → geometry → enforcement-identity → live face → live NIM → composite reconciliation)
- `outputs/lon_d6b3_havering_enforcement_identity_recovery/`
- `outputs/lon_d6b4_havering_enforcement_identity_expansion/`
- `outputs/lon_d11a_toid_generalised_location_recovery/`
- `outputs/lon_d10ev_ev_charging_source_recovery/`
- `outputs/lon_d11c_live_london_face_route_fix/`
- `outputs/lon_d13c_london_final_prehero_closure/LON_D13C_HARNESS_REPORT.json` — **the accepted London source of truth**
- 4070: `/data/citybrain/from_3090/london_d13c_final_prehero_closure_v1/`
- Live: `http://192.168.1.48:8080/london`, `http://192.168.1.48:8080/api/london/*`
- Hero package: `outputs/lon_hero_dual_scenario_package/`

**Boards:**
- `TXRCityBrain_MissionControl.html`
- `TXRCityBrain_ToDo.html`
- `TXRCityBrain_NYC_HeroCascade.html`

---

## 8. What this document explicitly does NOT claim

To be read alongside this doc — every item below is either in-progress, deferred, or not yet started, and is tracked in docs 02–04:

- The application is not formally snapshotted (A9 / G1 pending — see doc 02)
- London Flow 3/4/5 sub-cartridges are accepted only as bounded review-context extensions through `LON-FLOWX-D6`; they are not emergency, dispatch, public-order, utility-control, health, legal, or certified affected-asset systems
- A live event fabric does not exist (L4 — see doc 03)
- A runtime perception pipeline does not exist (L7 — see doc 03)
- Domain simulators do not exist (SUMO, pandapower, EPANET — see doc 03)
- A NYC OpenUSD twin does not exist (see docs 02 and 03)
- Incident and Plan cognition modes do not exist (see doc 03)
- A persona layer does not exist (see doc 03)
- Singapore Flow 4 accepted proof and other unlisted flow/city combinations do not exist yet (see doc 03, doc 04, and `TXRCityBrain_CityCore_Subcartridge_Model.md`)
- Dubai and oil & gas cartridges do not exist (see doc 04)
- Earth-2, CorrDiff, Cosmos rollouts, NeMo Curator, cuVS / NeMo Retriever, full Metropolis / VSS are not built (see doc 04)
- The Executive Summary, rename pass, repo/README, and demo video are not produced (see doc 02)

---

*End of doc 01. See doc 02 for the near-term Application Snapshot definition of done.*

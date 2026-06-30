# CITYBRAIN FULL PROJECT HANDOVER — CONSOLIDATED

This is the single-file version of the full handover pack.

---

# CityBrain Full Project Handover — START HERE

Date: 2026-06-29  
Project: CityBrain / Digital Twin / Smart City Brain  
Purpose: full-state handover for a new ChatGPT project conversation.

This handover is intentionally broader than the recent Track 1 D2 / Track 2 summary. It covers:

- the overall CityBrain product vision and claim boundaries
- current certified platform state and addenda
- per-city data/flow status for Barcelona, NYC, Chicago, London, and Singapore
- Track 1 runtime/body status through D2 closeout
- Track 2 FlowPack/oracle/promotion status through R5
- infrastructure and GPU box roles
- Omniverse / 3D data guidance
- next tasks and exact bootstrap prompt for the new conversation

## Current one-line state

CityBrain has reached a governed Platform v1 review/context foundation with multi-city FlowPacks, accepted/addendum-tracked flows, and a closed Track 1 D2 bounded runtime body: bounded live/polled events, perception candidate events, and SUMO simulated events feed one governed event fabric with current state, replay, and EvidenceBundle smoke while preserving observed/context, candidate/review, and simulated/context boundaries.

## What just closed

Track 1 D2 closeout completed:

- Task: `MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP`
- Status: `PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS`
- Output root: `outputs/main_track1_d2_closeout_and_d3_roadmap`
- Runner: `scripts/run_main_track1_d2_closeout_and_d3_roadmap.py`
- Decision: `MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json`

The intentional limitation carried forward is SUMO D2's Barcelona routeable-equivalent limitation: city-derived traffic-section coordinates are used as a bounded SUMO-routeable equivalent, not a complete routable street graph or certified traffic model.

## Immediate next task

Recommended next Track 1 task:

`MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`

This begins D3: hardening the bounded D2 runtime into a service-grade multi-city runtime twin. Do not start D4/Omniverse product work yet unless explicitly chosen.

## Current active queue

1. `MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`
2. `MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS`
3. `MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE`
4. `MAIN-PERCEPTION-D3-REVIEW-API`
5. `MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING`
6. `MAIN-SUMO-D3-SCENARIO-CATALOG`
7. `MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE`

Track 2 is closed for this cycle. It does not need more work unless we run a control-doc reconciliation or decide to apply future evidence refinements.

## How to use this pack in the new conversation

Upload the ZIP to the new conversation and paste the text from `08_NEW_CHAT_BOOTSTRAP_PROMPT.md`.

The new assistant should first confirm:

- Track 1 D2 is closed with limitations.
- Track 2 is closed through R5 evidence refinement.
- The next active task is `MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`.
- Claim boundaries remain strict: no enforcement, dispatch, public-safety command, traffic/transit/port control, health determination, routing recommendation, certified impact, or production readiness claim.

---

# CityBrain Operating Model, Vision, and Boundaries

## Product vision

CityBrain is a city-scale digital twin / smart brain. The core idea is not “a long video” or a single sequence model. A city is a typed, located, temporal graph with many coupled networks:

- road
- rail/transit
- water
- power
- communications
- land/building/permitting
- environment/climate
- public realm / civic service
- social/economic context

The system should combine:

- traditional deterministic analytics where appropriate
- graph/data methods
- simulation
- perception
- evidence retrieval
- generative AI only where useful, especially summarization/briefing/evidence narration

Important design principle from the project: do not “throw an LLM at everything.” Mean-time-to-failure, trends, routing/simulation, tabular analytics, graph joins, physics-like network propagation, and deterministic gates should use defined methods where possible.

## Maturity ladder used in the project

These D-levels are internal delivery-depth gates:

- `D1`: proof / safe concept demonstration
- `D2`: bounded runtime capability
- `D3`: hardened service runtime / multi-city runtime twin
- `D4`: product/operator/3D/Omniverse control-room experience
- `D5`: production/enterprise/regulated deployment readiness

Current state: Track 1 D2 is closed; D3 is next.

## Strict claim boundaries

Across all tracks, the system must not claim:

- production readiness
- autonomous monitoring
- confirmed legal violation
- identity inference
- face recognition
- biometric inference
- public-safety command
- dispatch recommendation
- enforcement recommendation
- health determination
- routing recommendation
- traffic-control command
- transit-control command
- port/vessel-control command
- utility-control command
- certified impact
- certified affected asset/building
- policing determination

Allowed current claims:

- governed evidence platform
- bounded runtime proof
- review/context-only
- simulated/context-only
- candidate/review-only perception events
- deterministic EvidenceBundle smoke
- bounded current-state API smoke
- no action taken

## Project-wide non-mutation rule

Most tasks must be additive. Unless a task explicitly says otherwise, do not mutate:

- PV1 D19-D22 outputs
- A9/G1 snapshot outputs
- generated platform state
- accepted flow status
- city data landing/prep roots
- D1/D2 output roots
- previous snapshot addenda
- raw secrets or `.env`/API-key materials

New work should write to a new `outputs/...` root and create audits proving no mutation.

## Primary deliverable posture

CityBrain is currently a governed review/context platform with bounded runtime proof. It is not a production command system.

The useful near-term story is:

- city data and flow evidence are landed and organized
- accepted flows are documented with limitations
- runtime events can be polled/generated/candidate/simulated
- current state and replay are available
- EvidenceBundles ground briefings
- D3 will harden the service layer

---

# Current Certified State and Addenda

## Key platform snapshot lineage

The project uses additive snapshots/addenda rather than mutating prior certified state.

Important platform snapshot status:

- PV1 D19/D20/D21/D22 completed green with final status:
  `PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT`
- Final output root:
  `outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate`
- Results:
  - D19 action policy PASS
  - D20 guardrail harness PASS
  - D21 composite snapshot PASS
  - D22 final audit PASS
  - forbidden actions blocked

## A9/G1 snapshot closeout

- Task: `MAIN-PLATFORM-A9-G1-SNAPSHOT-CLOSEOUT-R1`
- Status: `PASS_MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1`
- Output root: `outputs/main_platform_a9_g1_snapshot_closeout_r1`
- Runner: `scripts/run_main_platform_a9_g1_snapshot_closeout_r1.py`
- Checks passed:
  - platform state freeze
  - resolver regression
  - oracle/evidence smoke
  - face/trace/briefing smoke
  - claim-boundary audit
  - no-mutation audit
  - secret redaction audit
  - 34 file hashes
- No upstream PV1 D19-D22 mutation, no R2/R3 rewrite, no Barcelona gate rerun, no data downloads, no new flow promotions.

## Snapshot addenda

Known addenda state:

- `PV1-SNAPSHOT-ADDENDUM-R2`: passed during Barcelona full absorption stage.
- `PV1-SNAPSHOT-ADDENDUM-R3`: added during Barcelona F1-F6 flow acceptance closeout.
- `PV1-SNAPSHOT-ADDENDUM-R4`: passed in `MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1`.
- `PV1-SNAPSHOT-ADDENDUM-R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT`: passed in `CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1`.

R4 applied additively:

- `LON-F7X` -> `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `CHI-F2X` -> `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F5X` -> `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `PV1-SNAPSHOT-ADDENDUM-R4` -> `PASS_PV1_SNAPSHOT_ADDENDUM_R4`

R5 did not change statuses. It refined evidence/source weighting for `CHI-F2X` and `CHI-F5X`.

## Control docs

Original control docs mentioned by the user and treated as project operating docs:

- Mission Control — addendum R1
- To-Do — addendum R1
- Current Certified State — addendum R1
- Platform v1 DoD — addendum R1
- Full Vision Completion Map — addendum R1
- Codex/Claude Handoff — addendum R1
- Addendum R1 manifest

A later reconciliation prompt was prepared for `MAIN-CONTROL-DOCS-ADDENDUM-R2-RECONCILIATION`, but in this handover the latest operational truth is the actual task completions through Track 1 D2 closeout and Track 2 R5.

Potential later housekeeping task:
`MAIN-CONTROL-DOCS-ADDENDUM-R6-POST-D2-R5-RECONCILIATION`
or equivalent, only if the user wants the Mission Control docs refreshed after D2/R5.

---

# City Data and Flow Status by City

## Barcelona

Barcelona is the most complete accepted multi-flow city in this cycle.

### Cadastre recovery

Task: `BARC-CADASTRE-RECOVERY-D1`  
Status: `PASS_BARC_CADASTRE_RECOVERY_D1`

Recovered via Spanish Cadastre ATOM ZIP path with municipality `08900-BARCELONA`.

Recovered assets:

- Parcels: `RECOVERED_ATOM_ZIP`, 16,182,621 bytes, 78,371 features
- Buildings: `RECOVERED_ATOM_ZIP`, 44,624,867 bytes, 69,893 features
- Addresses: `RECOVERED_ATOM_ZIP`, 3,221,259 bytes, 90,258 features

### Barcelona core and flow acceptance

- `BARC-CORE-D3`: `ACCEPTED_CITY_CORE_WITH_LIMITATIONS`
- `BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1`: `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `PV1-SNAPSHOT-ADDENDUM-R2`: `PASS_PV1_SNAPSHOT_ADDENDUM_R2`
- `BARC-F1-F6-FLOW-ACCEPTANCE-CLOSEOUT-R1`: `PASS_BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1`

Accepted Barcelona flows:

- `BARC-F1`: `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `BARC-F2`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `BARC-F3`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `BARC-F4`: `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `BARC-F5`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `BARC-F6`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `BARC-F7`: `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`

### Barcelona full platform absorption

- `MAIN-SPINE-BARCELONA-FULL-ABSORB-R1`: `PASS_MAIN_SPINE_BARCELONA_FULL_ABSORB_R1`
- Generated platform state now includes Barcelona as a city, not just patch ledger.
- 4 cities and 24 flow rows in generated platform state at that point.
- Legacy `BARCELONA-*` flow IDs removed.
- Regression `no_legacy_barcelona_flow_ids: true`.

### Barcelona data landing

Task: `BARC-ALLFLOWS-DATA-LANDING-R1`  
Status: `PASS_PHASE_1_BREADTH`

Key totals:

- 56 sources represented
- 6,495,847 rows landed
- 238,522 features registered
- 39 files landed/registered
- ~2.04 GB landed/registered
- secret redaction PASS

Limitations:

- `amb_gtfs_rt`: `BLOCKED_REMOTE`
- `sentilo_connecta`: `ENDPOINT_VALIDATION_REQUIRED`
- `tmb_ibus`: `KEY_BLOCKED`
- raw TMB key scan: clean

### Barcelona consumption prep

Task: `BARC-ALLFLOWS-CONSUMPTION-PREP-R1`  
Status: `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`

Output root:
`outputs/barc_allflows_consumption_prep_r1`

Key totals:

- 56 sources
- 6,415 entity anchors
- 3,840 join candidates
- 1,432 staged events
- 666 staged observations
- 140 EvidenceBundle samples
- 175 smoke queries
- F1-F7 consumption bundles
- DuckDB mart created

Known limitation:
Bicing GBFS parquet stub initially invalid/too small for DuckDB source view; later repaired in FlowPack cleanup into DuckDB from local raw JSON with 541 station info rows and 541 station status rows.

## New York City

### Source scan

NYC source scan covered Socrata/SODA2 sources across F1-F7.

Important sources:

- DOT Traffic Speeds: ~108.9M rows (`i4gi-tjb9`), date field `data_as_of`
- 311 2020-present: ~21.6M rows (`erm2-nwe9`)
- DOB permits/complaints/violations/NOW
- PLUTO
- MVC
- LL84
- FVI
- facilities and others

### Data landing

Task: `NYC-ALLFLOWS-DATA-LANDING-R1`  
Status: `PASS_WITH_LIMITATIONS`

Key totals:

- 17,573,777 rows landed
- 25 full-complete tabular sources
- 13 capped-breadth sources
- 5 direct metadata-only sources
- 2 tile/file-strategy sources

DOT Traffic Speeds:

- 30-day window from `2026-05-29T00:00:00`
- 892,752 rows
- `WINDOWED_COMPLETE`

Rows by flow:

- F1: 6,346,826
- F2: 8,754,051
- F3: 14,197,287
- F4: 7,869,980
- F5: 1,500,291
- F6: 195,196
- F7: 12,169,508

### Consumption prep

Output root:
`outputs/nyc_flow_consumption_prep_r1`

Key totals:

- 46 sources
- 57,297 anchors
- 57,297 join candidates
- 31,263 event rows
- 7 flow bundle folders
- candidate gates generated F1-F7

Readiness:

- F2 and F5: `FLOW_CONSUMPTION_READY_CANDIDATE`
- F1, F3, F4, F6, F7: `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`

Promotion/acceptance from later batch:

- `NYC-F2`: already accepted/mounted no-op during R4 batch
- `NYC-F5`: already accepted/mounted no-op during R4 batch, with review/context limitations

## Chicago

### Source scan

Chicago D1 allflows source scan included 64 candidate sources across F1-F7.

Strong/high-priority sources include:

- Taxi Trips 2013-2023: ~211M
- TNP Trips 2023-2024: ~174M
- TNP Trips 2025: ~124M
- Chicago Traffic Tracker: ~101M
- Cook parcels Chicago-filtered: ~22.86M
- 311: ~14.15M
- Open Air individual: ~9M
- Transportation Department Permits: ~2.28M
- Business Licenses
- crashes
- other city sources

CTA live APIs are key-blocked.

### Data landing

Task: `CHI-ALLFLOWS-DATA-LANDING-R1`  
Status: `PASS_WITH_LIMITATIONS`

Output root:
`outputs/chi_allflows_data_landing_r1`

Key totals:

- 64 sources tracked
- 20,190,169 rows landed
- 1,007 files written
- ~3.13GB disk footprint
- 57 normalized source folders

Landing status counts:

- FULL: 39
- CAPPED_BULK: 15
- BOUNDED_SAMPLE: 3
- METADATA_ONLY: 7

Known bounded/blocked:

- `311_service_requests`: 550,000 / 14,150,892, bounded sample due timeout after partial landing
- `tnp_trips_2025`: 100,000 / 124,005,107, bounded sample
- `traffic_tracker_historical`: 50,000 / 101,139,655, bounded sample
- `taxi_trips`, `tnp_trips_2023_2024`: metadata-only due remote timeout
- CTA live APIs: metadata-only/key-blocked
- `cta_gtfs_static`: blocked remote HTTP 406

### Consumption prep

Task: `CHI-ALLFLOWS-CONSUMPTION-PREP-R1`  
Status: `FLOW_CONSUMPTION_READY_CANDIDATE`

Actual output root:
`outputs/chi_flow_consumption_prep_r1`

Canonical root later created:
`outputs/chi_allflows_consumption_prep_r1`

Key totals:

- 64 sources audited
- 54 silver DuckDB views
- 587,306 candidate anchors
- 587,306 candidate joins
- 210,316 event staging rows
- 36,377 observation staging rows
- 146 feature cube rows
- 140 EvidenceBundle samples
- 175 smoke queries
- F1-F7 flow bundles

Known source view issues from prep:

- `arterial_daily_traffic`
- `police_districts`
- `street_center_lines`

These had manifest rows but empty-object schemas and were excluded until clean redownload/repair.

### Promotion R4

R4 applied:

- `CHI-F2X`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F5X`: `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F7`: already accepted/mounted no-op / evidence flow

### Chicago F2/F5 strengthening

Task:
`CHI-F2X-F5X-DATA-STRENGTHENING-R1`

Status:
`PASS_CHI_F2X_F5X_DATA_STRENGTHENING_R1`

Output root:
`outputs/chi_f2x_f5x_data_strengthening_r1`

Created additive strengthened mart:
`CHI_F2X_F5X_STRENGTHENED_MART.duckdb`

Added strengthened tables/views:

- `strengthened.f2_source_coverage`
- `strengthened.f5_source_coverage`
- `strengthened.f5_311_water_flood_slice`
- `strengthened.f5_311_water_flood_category_counts`
- `strengthened.f5_sensor_source_counts`
- `strengthened.f2_primary_source_counts`

Key results:

- F2 matrix covers 15 planning/compliance sources.
- F5 matrix covers 16 climate/asset-risk sources.
- F5 targeted 311 water/sewer/flood/storm slice: 20,391 landed rows.
- F2 now weights parcels, buildings, permits, violations, zoning above business licenses.
- F5 now weights Open Air, green infrastructure, environmental context, and targeted 311 above broad bounded 311.
- Generated 20 strengthened F2 EvidenceBundles and 20 strengthened F5 EvidenceBundles.
- Generated 25 F2 smoke queries and 25 F5 smoke queries.
- Generated 10 F2 negative tests and 10 F5 negative tests.

### R5 evidence refinement

Task:
`CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1`

Status:
`PASS_CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1`

R5 addendum status:
`PASS_PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT`

Output root:
`outputs/chi_f2x_f5x_recheck_for_r5_addendum_r1`

Key result:

- `CHI-F2X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F5X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- no promotion gate run
- no platform state applied in place
- R4 remains valid
- R5 refines evidence/source-weighting basis only

## London

### Source scan

London 7-flow scan status:
`PASS_WITH_SOURCE_LIMITATIONS`

33 sources scanned.

London uses:

- native CKAN/Data London resources
- TfL APIs
- London Air
- EA flood-monitoring APIs
- data.police.uk
- planning.data.gov.uk
- existing XDATA/local manifests

Strongest flows: F3/F4/F5/F7.  
F6 weakest and aggregate/context-only.

Key source context:

- LFB incidents: 1,976,254
- LFB mobilisations: 2,788,962
- fusion existing XDATA: 4,769,591
- TfL road disruptions, line status
- London Air
- EA flood areas/stations

### Data landing

Task:
`LON-ALLFLOWS-DATA-LANDING-R1`

Status:
`PASS_WITH_LIMITATIONS`

Output root:
`outputs/lon_allflows_data_landing_r1`

Key totals:

- 33/33 sources represented
- 180 files landed/registered
- 10,937,414 rows landed/registered
- no `.part` files
- secret scan PASS
- cap ladder through 25M recorded

New harvest included:

- LAEI files: 560,944,000 bytes
- ONS/population files: 390,139,698 bytes
- MPS crime dashboard files: 275,364,119 bytes
- IMD/deprivation
- Planning Local Plan
- noise
- energy
- data.police.uk bounded windows
- EA station-first measures
- London Air site/species JSON
- NHS A&E resource capture

Remaining landing limitation:
`london_air_daily_no2` `CAP_PARTIAL`.

### Consumption prep

Task:
`LON-ALLFLOWS-CONSUMPTION-PREP-R1`

Status:
`FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`

Output root:
`outputs/lon_allflows_consumption_prep_r1`

Key totals:

- 33 sources audited
- 21 silver source families
- 3,248,283 silver rows
- 31,066 entity anchors
- 6,000 join candidates
- 970 staged events
- 495 staged observations
- DuckDB mart `LON_FLOW_MART.duckdb`
- EvidenceBundle samples + smoke packs for F1-F7
- no-overclaim scan PASS

Flow readiness:

- F3, F4, F5, F7: `FLOW_CONSUMPTION_READY_CANDIDATE`
- F1, F2: `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`
- F6: `PARTIAL_FLOW_CONSUMPTION_CANDIDATE`

### Promotion R4

R4 accepted:

- `LON-F7X` -> `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`

The following London flows were already accepted/mounted no-op regression checks during R4:

- `LON-F3X`
- `LON-F4X`
- `LON-F5X`

They remain bounded by review/context limitations.

## Singapore

Singapore Data D1 completed but not green.

Status:
`FAIL`

Reason:
LTA DataMall returned HTTP 401 for supplied SDK key; equivalent header casing also failed.

Public sources landed successfully.

Key facts:

- LTA authenticated: FAIL
- LTA endpoints probed: 25
- LTA endpoints pulled: 0
- NEA/data.gov.sg public endpoints: 6 HTTP 200 current snapshots plus 2 forecast 429
- OneMap: partial/token-limited
- PM2.5 regions: 5
- rainfall stations: 76
- wind-speed stations: recorded
- The blocker is LTA auth/key, not public-data path.

Singapore should not be treated as accepted or green until LTA auth is fixed or a public-source-only scope is explicitly defined.

---

# Track 1 Runtime / Body Layer Status

Track 1 is the runtime/body layer: event fabric, perception candidate intake, SUMO simulation producer, and integrated runtime smoke.

## D1 completed

Completed D1 tasks:

- `MAIN-PLATFORM-EVENT-FABRIC-D1` -> `PASS_MAIN_PLATFORM_EVENT_FABRIC_D1`
- `MAIN-PERCEPTION-CANDIDATE-EVENT-D1` -> `PASS_MAIN_PERCEPTION_CANDIDATE_EVENT_D1`
- `MAIN-SUMO-SIMULATION-D1` -> `PASS_MAIN_SUMO_SIMULATION_D1`
- `MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1` -> `PASS_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1`

D1 integrated smoke totals:

- 156 total events
- 128 Event Fabric base events
- 16 Perception candidate events
- 12 SUMO simulation events
- 3 replay scenarios
- 0 event ID collisions

Family breakdown:

- civic_service_status: 52
- mobility_status: 40
- incident_context: 36
- perception_candidate: 16
- simulation_mobility: 12

D1 proved the three event producer families could be integrated offline with no mutation and correct claim boundaries.

## D2 completed

D2 sequence:

1. `MAIN-EVENT-FABRIC-D2`
2. `MAIN-PERCEPTION-D2`
3. `MAIN-SUMO-D2`
4. `MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE`
5. `MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP`

### Event Fabric D2

Status:
`PASS_MAIN_EVENT_FABRIC_D2`

Purpose:
lightweight Python/DuckDB runtime layer.

Capabilities:

- poller registry
- durable cursor table
- idempotent append log
- dedupe keys
- current-state materializer
- bounded scheduler smoke
- replay-from-cursor
- stdlib HTTP smoke endpoints:
  - `/health`
  - `/current-state`
  - `/replay`

D2 event fabric is the substrate for Perception D2 and SUMO D2.

### Perception D2

Status:
`PASS_MAIN_PERCEPTION_D2`

Output root:
`outputs/main_perception_d2`

Runner:
`scripts/run_main_perception_d2.py`

Key results:

- Event Fabric D2 dependency verified.
- D1 deterministic fixture lane preserved: 37 D1 observations.
- Sample-media lane passed using local read-only clips from `cascade_clips_manifest_and_downloader/cascade_clips/`.
- 47 detection observations.
- 22 candidate events, including 6 sample-media candidate events.
- 22 Event Fabric D2-compatible envelopes.
- 22 human-review packets.
- isolated overlay append passed with 22 duplicate/idempotency hits.
- current-state DuckDB created and populated.
- 3 replay scenarios passed.
- EvidenceBundle smoke, negative tests, claim-boundary audit, no-mutation audit, secret audit, and hashes passed.

Limitation:
`ffprobe` unavailable, so video metadata is `metadata_limited_ffprobe_unavailable`; sample-media lane still passed because local media assets existed and deterministic fallback detection JSON was generated.

Boundary:
candidate/review-only; no identity, biometric, violation, enforcement, dispatch, or production CCTV claim.

### SUMO D2

Status:
`PASS_MAIN_SUMO_D2_WITH_LIMITATIONS`

Output root:
`outputs/main_sumo_d2`

Runner:
`scripts/run_main_sumo_d2.py`

Key results:

- Native SUMO 1.27.1 ran 3 scenarios:
  - baseline
  - slowdown disruption
  - recovery
- Network: 30 nodes, 68 edges.
- Produced 1,200 observations.
- Produced 24 simulation events.
- Produced 24 Event Fabric D2-compatible envelopes.
- Overlay append/current state passed without mutating Event Fabric D2.
- Replay, EvidenceBundle smoke, negative tests, claim-boundary audit, no-mutation audit, secret audit passed.
- Raw TMB key scan: no hits.

Intentional limitation:
Barcelona traffic-section geometry was usable and city-derived, but it is point-chain context, not a full routable street graph. A bounded SUMO-routeable equivalent was generated from official Barcelona traffic-section coordinates and surfaced as a limitation.

Boundary:
simulated/context-only, aggregate-only, not observed truth, not routing/control, not certified traffic model.

### Integrated Runtime Smoke D2

Status:
`PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS`

Output root:
`outputs/main_track1_d2_integrated_runtime_smoke`

Runner:
`scripts/run_main_track1_d2_integrated_runtime_smoke.py`

Key results:

- Event Fabric D2: `PASS_MAIN_EVENT_FABRIC_D2`
- Perception D2: `PASS_MAIN_PERCEPTION_D2`
- SUMO D2: `PASS_MAIN_SUMO_D2_WITH_LIMITATIONS`
- Unified events: 91
- Event ID collisions: 0
- Producer counts:
  - Event Fabric D2: 45
  - Perception D2: 22
  - SUMO D2: 24
- Lifecycle counts:
  - observed: 43
  - late/out-of-order: 1
  - expired: 1
  - candidate: 22
  - simulated: 24
- Current-state DuckDB created with separated observed/context, candidate/review, and simulated/context tables.
- API smoke, replay, EvidenceBundle smoke, negative tests, claim-boundary audit, no-mutation audit, secret audit, and hashes all passed.

Limitation:
`WITH_LIMITATIONS` preserves SUMO D2 Barcelona routeable-equivalent limitation.

### D2 closeout

Status:
`PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS`

Output root:
`outputs/main_track1_d2_closeout_and_d3_roadmap`

Runner:
`scripts/run_main_track1_d2_closeout_and_d3_roadmap.py`

Key results:

- all four D2 gates inspected and valid
- certified D2 state written
- capability ledger written with 14 capabilities
- evidence index written with 43 artifacts, none missing
- D3 backlog written with 7 ordered tasks
- no-mutation audit passed
- secret audit passed
- hashes written

Accepted D2 close sentence:
CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.

## D3 roadmap

D3 theme:
harden the bounded D2 runtime into a service-grade multi-city runtime twin.

Roadmap workstreams:

1. `MAIN-EVENT-FABRIC-D3`
   - service mode
   - stronger API contract
   - multi-city adapter expansion
   - observability
   - cursor recovery
   - retention policy
   - replay API hardening
   - error budgets / health checks
   - 4070/3090 deployment profile where relevant

2. `MAIN-PERCEPTION-D3`
   - DeepStream/Metropolis path on 4070
   - model-output adapter
   - real sample camera/video pipeline
   - stronger camera/zone governance
   - review API/UI integration
   - media metadata hardening
   - privacy/redaction posture

3. `MAIN-SUMO-D3`
   - improve network extraction beyond point-chain routeable equivalent
   - expand Barcelona/London/NYC/Chicago subsets
   - scenario catalog
   - calibration against observed mobility signals
   - compare simulated vs observed mobility context
   - not routing/control

4. `MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE`
   - unified runtime API
   - durable multi-producer service smoke
   - trace/debug tooling
   - EvidenceBundle/briefing integration
   - dashboard/control-room readiness

Recommended first D3 task:
`MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`

---

# Track 2 / Parallel FlowPack, Oracle, Promotion Status

Track 2 is the flowpack/oracle/promotion layer. It is closed for this cycle.

## Flow Consumption Contract D1

Task:
`MAIN-PLATFORM-FLOW-CONSUMPTION-CONTRACT-D1`

Status:
`PASS_MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_WITH_LIMITATIONS`

Output root:
`outputs/main_platform_flow_consumption_contract_d1`

Key outputs:

- `MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_DECISION.json`
- `CITY_FLOW_PACK_REGISTRY.json`
- `FLOW_PACK_SCHEMA.json`
- `EVIDENCEBUNDLE_RUNTIME_SCHEMA.json`
- `FLOW_PACK_LOADER_REPORT.md`
- runner: `scripts/run_main_platform_flow_consumption_contract_d1.py`

Initial load status:

- NYC loaded with limitations
- Barcelona loaded with limitations
- Chicago loaded with limitations from fallback root
- London loaded

Initial limitations:

- NYC smoke pack Markdown/text not JSONL
- Barcelona DuckDB non-empty `source_view_errors`
- Chicago expected allflows root absent, fallback root used, smoke pack not JSONL
- London loaded cleanly

## Oracle FlowPack Bridge D1

Task:
`MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1`

Status:
`PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_WITH_LIMITATIONS`

Output root:
`outputs/main_platform_oracle_flowpack_bridge_d1`

Key facts:

- 12 smoke queries
- 12 deterministic EvidenceBundle runtime objects
- runtime packs loaded for NYC/BARC/CHI/LON
- read-only DuckDB adapter where available
- no mutation

Initial limitations:

- London F3/F4/F7 mart reads hit missing Python `pytz` in DuckDB/Pandas path, fallback to runtime samples.
- Intentional Barcelona missing-view smoke recorded as active limitation instead of expected negative test.

## FlowPack Limitation Cleanup R1

Task:
`MAIN-PLATFORM-FLOWPACK-LIMITATION-CLEANUP-R1`

Status:
passed

Output root:
`outputs/main_platform_flowpack_limitation_cleanup_r1`

Cleaned results:

- NYC: `LOADED`, canonical JSONL smoke pack with 175 rows
- Barcelona: `LOADED`, active `source_view_errors = 0`; Bicing GBFS repaired into DuckDB from local raw JSON with 541 station info rows and 541 station status rows
- Chicago: `LOADED`, canonical root created at `outputs/chi_allflows_consumption_prep_r1/`, JSONL smoke pack with 175 rows
- London: `LOADED`, regression clean

Oracle recheck:

- `PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_RECHECK`
- 12 smoke queries pass
- London `pytz` fallback removed by switching bridge to bounded metadata/count queries
- Barcelona intentional missing-view test reclassified as `PASS_EXPECTED_MISSING_VIEW_REPORTED`
- no active oracle runtime limitations remain

## Flow Promotion Gate Runner D1

Task:
`MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1`

Status:
`PASS_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1`

Output root:
`outputs/main_platform_flow_promotion_gate_runner_d1`

Dry-run evaluated 9 required flows.

No-op / already accepted or mounted:

- `NYC-F2`
- `NYC-F5`
- `LON-F3`
- `LON-F4`
- `LON-F5`
- `CHI-F7`

Promotable dry-run drafts:

- `LON-F7`
- `CHI-F2`
- `CHI-F5`

Dry-run patch/addendum drafts were marked `DRY_RUN_ONLY` and `requires_human_approval = true`.

## Flow Promotion Batch R1

Task:
`MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1`

Status:
passed

Applied additively:

- `LON-F7X` -> `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `CHI-F2X` -> `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F5X` -> `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `PV1-SNAPSHOT-ADDENDUM-R4` -> `PASS_PV1_SNAPSHOT_ADDENDUM_R4`

No-op flows were only regression checks and stayed unchanged. Barcelona F1-F7 stayed unchanged. PV1 D19-D22 and A9/G1 stayed unchanged.

## Chicago F2/F5 strengthening and R5

See the Chicago section in `03_CITY_DATA_AND_FLOW_STATUS_BY_CITY.md`.

Short version:

- `CHI-F2X-F5X-DATA-STRENGTHENING-R1`: `PASS_CHI_F2X_F5X_DATA_STRENGTHENING_R1`
- `CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1`: `PASS_CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1`
- R5 addendum status:
  `PASS_PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT`
- `CHI-F2X` and `CHI-F5X` remain accepted context flows with limitations.
- R5 only refines evidence/source weighting.
- No promotion gate run and no platform state applied in place.

## Track 2 final state

Track 2 is closed for this cycle:

- FlowPack contract: done
- Oracle bridge: done
- FlowPack cleanup: done
- Promotion runner: done
- Promotion batch R1: done
- Chicago F2/F5 strengthening: done
- Chicago R5 evidence refinement: done

No urgent Track 2 work remains.

Possible later housekeeping:

- control-doc reconciliation to record R4/R5 and Track 1 D2 closeout
- future flow promotions only if new city/flow data materially improves

---

# Infrastructure, Hardware, and Runtime Roles

## GPU / compute boxes

The project has a distributed local hardware plan.

### DGX Spark / GB10 box

Role:
the brain / AI factory.

Intended workloads:

- NIM microservices
- LLM
- VLM
- embeddings
- reranker
- NeMo Agent Toolkit
- NeMo Guardrails
- NeMo Retriever
- possible fine-tuning where appropriate

Rationale:
128GB unified memory can host the model zoo at once; NVIDIA stack preinstalled; ARM64 native containers should be used where needed.

### RTX 5090 laptop

Role:
simulation + demo driver.

Intended workloads:

- Omniverse / USD Composer
- twin visualization
- control room
- Cosmos generation runs
- screen recording / demo workflows

Rationale:
fast rendering GPU and primary interactive machine; Blackwell useful for Cosmos/visual work.

### RTX 3090 PC (`txr-3090`)

Role:
data + graph + simulation.

Known status:

- IP: `192.168.1.148`
- RTX 3090
- SSH PASS
- Docker GPU PASS
- RAPIDS image `rapidsai/notebooks:26.06-cuda12-py3.11-amd64` PASS
- real-data RAPIDS cuDF/cuGraph probe PASS:
  `PASS_REAL_DATA_RAPIDS_PROBE`
- CityBrain sync complete:
  - processed data 3.4G
  - D2b, D3a, D6b outputs and source scripts present under `/data/citybrain`

Intended workloads:

- RAPIDS cuDF/cuGraph/cuSpatial
- cuOpt later
- vector DB
- simulators such as SUMO / pandapower / EPANET
- domain graph and analytics jobs

Deferred:
cuOpt until A6; Triton until specific perception model.

### RTX 4070 PC (`txr-4070`)

Role:
eyes + app.

Known status:

- IP: `192.168.1.48`
- RTX 4070
- SSH PASS
- Docker GPU PASS
- Node/npm/pnpm PASS
- Caddy PASS
- `/`, `/map`, `/trace`, `/briefing`, `/status.json` all HTTP 200

Intended workloads:

- DeepStream / Metropolis perception
- orchestrator/API
- face/dashboard/trace/briefing app
- review UI/API in D3

## Installation/deferred infrastructure notes

- Heavy streaming infrastructure was intentionally not used in D2.
- Event Fabric D2 uses Python + DuckDB + JSONL/Parquet + stdlib HTTP smoke.
- D3 may define service mode but should still avoid claiming production readiness.
- D5 is where production deployment hardening belongs: auth/RBAC, SLOs, deployment automation, monitoring, audit logs, security reviews.

## Local path convention

Most reported project artifacts are Windows paths under:

`C:/Users/hazem/Documents/CityBrain/`

In ChatGPT handovers these are reference paths, not accessible sandbox paths. Codex on the user machine should use those actual local paths.

---

# Omniverse / 3D / Coordinate Guidance

This project ultimately wants a city digital twin, likely with Omniverse/OpenUSD in D4.

Current priority is D3 runtime hardening. D4/Omniverse should not be started unless explicitly selected.

## 3D data scope

For 3D/Omniverse collection, only bring 3D data, not all backend/event/sensor data.

Minimum first Omniverse push:

- terrain / DEM
- textured ground / orthophoto
- buildings / building footprints + heights
- roads / road surface geometry
- bridges / overpasses / tunnels / elevated structures
- water surfaces
- trees / vegetation if readily available

Priority 1 additions:

- street furniture
- traffic lights/signs/gantries
- rail/tram/metro surface infrastructure
- stations/depots/terminals
- sidewalks/public squares/pedestrian areas
- retaining walls/stairs/ramps/embankments

Later:

- underground/utility corridors
- BIM/IFC key buildings
- interiors
- detailed facades / photogrammetry / LiDAR

Do not include tabular/event/sensor/complaint/schedule/permit/time-series data as 3D assets. Keep those in the backend/runtime/evidence system.

## Coordinate systems

Use two systems:

1. Source collection CRS
2. OpenUSD runtime coordinates

### Source CRS by city

Recommended source CRS:

- Barcelona: ETRS89 / UTM zone 31N, EPSG:25831
- London: British National Grid, EPSG:27700
- NYC: NAD83 / New York Long Island, EPSG:2263, ftUS -> convert to metres
- Chicago: NAD83 / Illinois East, EPSG:3435, ftUS -> convert to metres

Avoid using EPSG:4326 lat/lon or Web Mercator as engineering scene coordinates for 3D.

### OpenUSD runtime

Use:

- Z-up
- `metersPerUnit = 1.0`
- local ENU frame:
  - X = east
  - Y = north
  - Z = up
  - metres
- local origin per tile/district/city

Do not use giant absolute projected coordinates or lon/lat directly as scene coordinates.

## D4 expected scope

D4 likely includes:

- Omniverse/OpenUSD scene integration
- 3D city subset linked to runtime events
- scenario playback in 3D
- control-room UI
- human-review workflows
- trace/dashboard/briefing experience
- demo/product packaging

D4 still must not claim autonomous enforcement, dispatch, routing/control, certified impact, or production readiness unless D5 governance exists.

---

# New Chat Bootstrap Prompt

Paste this into the new ChatGPT Digital Twin project conversation after uploading this handover pack.

```text
You are continuing the CityBrain / Digital Twin project. Read the attached full project handover before answering.

Do not re-litigate completed gates. Treat the handover as the active state unless I provide newer output.

Current state:
- Track 1 D2 is closed with status PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS.
- Track 2 is closed through R5 evidence refinement.
- Barcelona F1-F7 are accepted with limitations.
- NYC/Chicago/London have accepted/mounted/promoted flows as documented.
- Singapore is not green because LTA DataMall auth failed.
- The next active main task is MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING.

Important boundary:
No enforcement, dispatch, public-safety command, health determination, routing/control, traffic/transit/port control, certified impact, production readiness, identity/biometric, or certified affected-asset claims.

First response:
Confirm the active queue and be ready to produce the next Codex prompt or critique the next output I paste.
```

---

# Next Codex Prompt — MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING

Use this as the next main prompt in the new conversation.

```text
MAIN CODEX TASK — EVENT FABRIC D3 SERVICE HARDENING

You are Main Codex for the CityBrain platform spine.

Task name:
MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING

Track:
Track 1 D3 — service-grade runtime hardening.

Goal:
Harden Event Fabric D2 from bounded runtime smoke into a service-grade runtime substrate for the CityBrain multi-city twin, while preserving all D2 claim boundaries.

D3 theme:
Harden the bounded D2 runtime into a service-grade multi-city runtime twin.

Current prerequisites:
- MAIN-EVENT-FABRIC-D2 = PASS_MAIN_EVENT_FABRIC_D2
- MAIN-PERCEPTION-D2 = PASS_MAIN_PERCEPTION_D2
- MAIN-SUMO-D2 = PASS_MAIN_SUMO_D2_WITH_LIMITATIONS
- MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE = PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS
- MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP = PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS

Known limitation to preserve:
SUMO D2 uses Barcelona city-derived traffic-section coordinates as a bounded SUMO-routeable equivalent. It is not a complete routable street graph, not a certified traffic model, and not routing/control.

Do not:
- mutate D2 roots
- mutate D1 roots
- mutate PV1 D19-D22
- mutate A9/G1
- mutate generated platform state
- mutate accepted flow state
- run flow-promotion gates
- start Perception D3
- start SUMO D3
- start D4/Omniverse work
- claim production readiness
- create dispatch, enforcement, public-safety, health, routing/control, traffic/transit/port control, or certified impact claims

Output root:
outputs/main_event_fabric_d3_service_hardening/

Runner:
scripts/run_main_event_fabric_d3_service_hardening.py

Required artifacts:
- README.md
- MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING.md
- MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json
- EVENT_FABRIC_D3_SERVICE_ARCHITECTURE.md
- EVENT_FABRIC_D3_API_CONTRACT.json
- EVENT_FABRIC_D3_API_CONTRACT.md
- EVENT_FABRIC_D3_SERVICE_MODE_REPORT.json
- EVENT_FABRIC_D3_CURSOR_RECOVERY_REPORT.json
- EVENT_FABRIC_D3_OBSERVABILITY_REPORT.json
- EVENT_FABRIC_D3_RETENTION_POLICY.md
- EVENT_FABRIC_D3_REPLAY_API_HARDENING_REPORT.json
- EVENT_FABRIC_D3_ERROR_BUDGET_HEALTH_REPORT.json
- EVENT_FABRIC_D3_DEPLOYMENT_PROFILE_4070_3090.md
- EVENT_FABRIC_D3_CURRENT_STATE.duckdb
- EVENT_FABRIC_D3_SERVICE_SMOKE_REPORT.json
- EVENT_FABRIC_D3_PRODUCER_COMPATIBILITY_REPORT.md
- EVENT_FABRIC_D3_NEGATIVE_TEST_REPORT.json
- CLAIM_BOUNDARY_AUDIT.md
- NO_MUTATION_AUDIT.md
- SECRET_REDACTION_AUDIT.md
- hashes.sha256

Phase 1 — inspect D2 closeout:
Read D2 closeout, capability ledger, evidence index, D2 limitation register, Event Fabric D2 outputs, Perception D2 append/compatibility outputs, SUMO D2 append/compatibility outputs, and integrated D2 runtime smoke outputs.

Phase 2 — define D3 service architecture:
Document a service-grade architecture that keeps the D2 lightweight approach but adds:
- service lifecycle
- stronger API contract
- durable cursor recovery
- observability
- retention policy
- replay API hardening
- health/error budget reporting
- deployment profile for 4070/3090 boxes

Do not introduce heavy Kafka/NATS/Redpanda unless explicitly justified as a future D4/D5 option. D3 may remain Python/DuckDB/HTTP if service-mode smoke is robust.

Phase 3 — API contract:
Define stable read-only APIs:
- /health
- /status
- /adapters
- /cursors
- /current-state
- /events
- /replay
- /evidencebundle-smoke

APIs must include claim_boundary, privacy_boundary, limitations, source_refs, and no_action_taken flags where relevant.

Phase 4 — service-mode smoke:
Run a bounded service smoke, not a daemon:
- start service
- poll/adapt small bounded inputs
- append idempotently
- materialize current state
- run API requests
- run replay requests
- stop service
- prove no lingering process required

Phase 5 — cursor recovery:
Simulate:
- clean restart
- cursor file/table recovery
- duplicate append
- late/out-of-order event
- adapter failure then recovery
- missing adapter limitation surfaced

Phase 6 — observability:
Add structured logs/metrics:
- adapter run counts
- append counts
- duplicate counts
- error counts
- late/expired counts
- current-state row counts
- replay duration
- API request status

Phase 7 — retention/replay hardening:
Define retention classes and replay safety:
- observed/context retention
- candidate/review retention
- simulated/context retention
- expired/superseded handling
- replay time window and event limit
- no operational commands generated

Phase 8 — producer compatibility:
Prove D3 remains compatible with:
- Perception D2/D3 candidate producers
- SUMO D2/D3 simulated producers
- future multi-city polling adapters

Phase 9 — negative tests:
Required:
- current-state API never returns commands
- candidate event not observed truth
- simulated event not observed truth
- duplicate append idempotent
- cursor recovery does not duplicate current state
- failed adapter limitation surfaced
- replay does not produce routing/control/dispatch/enforcement
- no platform mutation
- no flow promotion

Phase 10 — audits:
Claim-boundary, no-mutation, secret audits.

Phase 11 — final decision:
Allowed statuses:
- PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING
- PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_WITH_LIMITATIONS
- FAIL_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING

Expected final wording:
PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING

Recommended next task:
MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS
```

---

# State Ledger JSON

```json
{
  "date": "2026-06-29",
  "project": "CityBrain / Digital Twin",
  "current_focus": "Track 1 D3",
  "next_task": "MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING",
  "track1": {
    "d1": {
      "event_fabric_d1": "PASS_MAIN_PLATFORM_EVENT_FABRIC_D1",
      "perception_d1": "PASS_MAIN_PERCEPTION_CANDIDATE_EVENT_D1",
      "sumo_d1": "PASS_MAIN_SUMO_SIMULATION_D1",
      "integrated_r1": "PASS_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1"
    },
    "d2": {
      "event_fabric_d2": "PASS_MAIN_EVENT_FABRIC_D2",
      "perception_d2": "PASS_MAIN_PERCEPTION_D2",
      "sumo_d2": "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS",
      "integrated_runtime_smoke": "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS",
      "closeout_and_d3_roadmap": "PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS",
      "accepted_close_sentence": "CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.",
      "active_limitation": "SUMO D2 Barcelona city-derived traffic-section coordinates are a bounded SUMO-routeable equivalent, not a complete routable street graph or certified traffic model."
    },
    "d3_recommended_order": [
      "MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING",
      "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
      "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE",
      "MAIN-PERCEPTION-D3-REVIEW-API",
      "MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING",
      "MAIN-SUMO-D3-SCENARIO-CATALOG",
      "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE"
    ]
  },
  "track2": {
    "status": "closed_for_cycle",
    "flowpack_contract": "PASS_MAIN_PLATFORM_FLOW_CONSUMPTION_CONTRACT_D1_WITH_LIMITATIONS",
    "oracle_bridge": "PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_WITH_LIMITATIONS",
    "flowpack_cleanup": "PASS",
    "promotion_gate_runner": "PASS_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1",
    "promotion_batch_r1": "PASS",
    "r4": "PASS_PV1_SNAPSHOT_ADDENDUM_R4",
    "chi_f2_f5_strengthening": "PASS_CHI_F2X_F5X_DATA_STRENGTHENING_R1",
    "chi_r5_recheck": "PASS_CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1",
    "r5": "PASS_PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT"
  },
  "cities": {
    "barcelona": {
      "core": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
      "flows": {
        "BARC-F1": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "BARC-F2": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "BARC-F3": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "BARC-F4": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "BARC-F5": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "BARC-F6": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "BARC-F7": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS"
      },
      "data_landing": "PASS_PHASE_1_BREADTH",
      "consumption_prep": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS"
    },
    "nyc": {
      "data_landing": "PASS_WITH_LIMITATIONS",
      "consumption_prep": "candidate/ready with limitations by flow",
      "accepted_or_mounted": [
        "NYC-F2",
        "NYC-F5"
      ]
    },
    "chicago": {
      "data_landing": "PASS_WITH_LIMITATIONS",
      "consumption_prep": "FLOW_CONSUMPTION_READY_CANDIDATE",
      "accepted": {
        "CHI-F2X": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "CHI-F5X": "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "CHI-F7": "accepted/mounted evidence flow"
      },
      "r5_evidence_refinement": "complete"
    },
    "london": {
      "data_landing": "PASS_WITH_LIMITATIONS",
      "consumption_prep": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
      "accepted_or_mounted": {
        "LON-F3X": "accepted/mounted with review-context boundaries",
        "LON-F4X": "accepted/mounted with review-context boundaries",
        "LON-F5X": "accepted/mounted with review-context boundaries",
        "LON-F7X": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS"
      }
    },
    "singapore": {
      "status": "FAIL",
      "blocker": "LTA DataMall HTTP 401 for supplied SDK key"
    }
  },
  "global_forbidden_claims": [
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
    "certified impact",
    "certified affected asset/building"
  ]
}
```

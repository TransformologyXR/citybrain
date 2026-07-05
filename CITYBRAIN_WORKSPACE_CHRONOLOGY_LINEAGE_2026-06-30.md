# CityBrain Workspace Chronology and Lineage

Generated: 2026-06-30
Updated: 2026-07-01
Workspace: `C:\Users\hazem\Documents\CityBrain`

## Executive read

This workspace now has a small Git baseline on `master`, ending at `1b3a881 Add Hero USD twin HITL demo R2 milestone freeze runner`. The deeper lineage is still encoded mainly in filesystem timestamps, additive runner/output pairs, handover packs, manifests, and decision JSON files, because generated output roots and large data are intentionally not committed.

The project evolved from RTX/CityBrain vision documents into a governed city digital-twin platform with data landing, schema, graph, query/narration, web face/map surfaces, multi-city FlowPacks, Platform v1 review-only gates, Track 1 runtime gates, D4 operator/product/3D work, D4Y orchestration/runtime/contract hardening, and now D6 bounded local/replay product lanes.

The latest observed workspace tip is:

```text
outputs/main_citybrain_d6_r2_certified_state_and_handover_refresh
PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS
root file time: 2026-07-01 08:55:29
required upstreams: 6/6 found
optional upstreams: 15/15 found
closed tracks: 20
deferred tracks: 11
ready next tracks: 5
stale recommendation detection: PASS
blocking gaps: 0
recommended next: MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT
```

Important nuance: `CITYBRAIN_FULL_PROJECT_HANDOVER_CONSOLIDATED_2026-06-29_v2`, the integrated D4X/D5/Track2A handover, Hero/CERSEG readiness review, Demo R1, Demo R2, and R2 closeout/freeze are real milestones, but none is the final workspace state. Later files on 2026-07-01 show collateral R2, final package review, and the R2 certified-state/handover refresh.

## Workspace evidence base

- Git: `master` has 11 commits; latest is `1b3a881 Add Hero USD twin HITL demo R2 milestone freeze runner`.
- Top-level scale:
  - `outputs`: 99,596 files, about 23.76 GB, latest archive file 2026-07-01 08:57; latest output root observed is 2026-07-01 08:55.
  - `scripts`: 532 runner/helper/cache files, latest source runner 2026-07-01 08:55.
  - `data_landing`: 3,969 files, about 62.8 GB, latest 2026-06-28.
  - `citybrain_data_harvest_pack`: 3,951 files, about 29.0 GB.
  - `data`: 857 files, about 3.45 GB.
  - `nyc_mappluto_25v4_arc_shp`: about 2.17 GB.
  - `nyc_pluto_25v4_arc_csv`: about 369 MB.
- Output pattern: most work is additive. A task gets a `scripts/run_*.py` runner and a fresh `outputs/...` root with reports, manifests, audits, hashes, and usually a `*_DECISION.json`.
- Governance pattern: later gates repeatedly assert no-mutation, no-overclaim/claim-boundary, secret redaction, hash, and negative-test checks.

## Chronology

### 2026-06-20 to 2026-06-22: Vision and source landscape

The earliest top-level artifacts are strategic docs:

- `CityBrain_RTX_Roadmap.md`
- `CityBrain_RTX_Vision.md`
- `CityBrain_RTX_SyntheticData.md`
- `cities and data  sources (1).md`

This phase defined the broad CityBrain / digital twin / NVIDIA RTX direction and catalogued city/data-source possibilities before the runnable gate system existed.

### 2026-06-24: Foundation, schema, NYC base data

The workspace becomes executable and evidence-oriented:

- `TXRCityBrain_Onboarding.md`
- `TXRCityBrain_Schema_ERD.svg`
- `TXRCityBrain_Adapter_Handover.md`
- `PLUTO DATA DICTIONARY January 2026.md`
- `PLUTO README DOCUMENT.md`
- `requirements.txt`
- `txr_citybrain_prepare_parquet.py`
- `txr_citybrain_harness.py`
- `txr_citybrain_schema_v1.py`
- `txr_citybrain_schema_v1.schema.json`
- `txr_citybrain_build_a4_projection.py`
- `txr_citybrain_a4_graph_gate.py`

Large NYC PLUTO / MapPLUTO roots also appear. This is the base transition from concept documents into schema, adapters, harnesses, and NYC construction-compliance graph work.

### 2026-06-25: NYC graph, query, narration, map/route surface; London starts

This is a dense build day around the first serious CityBrain spine:

- A4/A5/A6/A8 runners and modules appear for district discovery, multi-district/citywide graph projection, Spark portability, operator query, evidence grounding, NeMo/NIM replay, narration, cuOpt review optimization, face payloads, map cache/API, and route overlays.
- `outputs/a5d7_citywide_briefings_v1` becomes the largest generated artifact family by file count, about 84k files.
- GPU/hardware handoff appears via `CITYBRAIN_GPU_BOXES_FOUNDATION_HANDOFF.md`.
- London begins late in the day with `txr_citybrain_lon_d4_identity_backbone_ingest.py` and related LON D1-D3 packs.

The lineage here is: NYC official datasets -> canonical schema -> graph projection -> deterministic evidence -> LLM/NIM narration constrained by grounding -> operator/web-facing surfaces.

### 2026-06-26: London Flow 2 matures; NYC Flow 3 source intake begins

London becomes the accepted second-city core:

- LON D4-D13c scripts and outputs cover identity backbone, PLD planning, UPRN backfill, LIDS bridge, enforcement/building-control, graph query smoke, operator query contract, London datastore/raw inventory, Local Plan semantics, TOID geometry, EV charging context, face layer, NIM wrapper/replay, composite accepted snapshots, and final prehero closure.
- Mission Control and ToDo HTML files are checkpointed before London D10z/D13/D13b/D13c/hero states.
- `txr_citybrain_lon_hero_dual_scenario_package.py` appears after the London chain.

Large source artifacts also land:

- `osopentoid_202605_csv_tq.zip`
- `Incidents_Responded_to_by_Fire_Companies_20260626.csv`
- `Motor_Vehicle_Collisions_-_Vehicles.csv`
- `EMS_incident_dispatch_data_description.xlsx`

By the end of the day, NYC Flow 3 work begins with source inventory/schema mapping and FDNY incident response slice ingest.

### 2026-06-27: NYC Flow 3, Singapore scout, A9/G1, Chicago, synthetic data factory

The workspace branches outward:

- NYC Flow 3 completes a D1-D10 chain: source inventory/download, FDNY incident response ingest, affected asset response context, candidate routing, governed evidence briefing, live Spark/NIM replay, face/map trace, hero package, accepted snapshot, and full-source propagation refresh.
- Singapore gets `txr_citybrain_sg_d1_source_api_scout.py`.
- A9/G1 board reconciliation and wire E2E appear.
- Chicago enters as a major city line: D1/D1b source scout/landing, D2/D2b identity/geography, D3/D3b civic event readiness, D4 dual-flow fork, F1/F7 dual flow, face layer/status fusion, hero package, and accepted snapshot.
- Platform v1 Synthetic Data Factory starts: PV1 SDF common, D1-D6, and run-all scripts/outputs.

This phase proves the project can replicate its gated pattern across cities and flows rather than remaining a single-city NYC demo.

### 2026-06-28: Platform v1 review-only snapshot, cross-city expansion, Track 2, docs update

This is the major consolidation day:

- PV1 infra D1/D2, cross-city ontology v2, event fabric contract, replay runner, current-state materializer, incident/plan modes, SUMO setup, HITL lifecycle, persona renderings, guardrail/action policy, and final Platform v1 snapshot work appear.
- `TXRCityBrain_01_CurrentCertifiedState*`, `TXRCityBrain_03_PlatformV1DoD*`, `TXRCityBrain_04_FullVisionCompletionMap*`, Mission Control, and ToDo files are updated/addended.
- Cross-city expansion and FlowX/XData tracks cover Barcelona, NYC, Chicago, and London data landing, consumption prep, review-flow acceptance, evidence bundles, replay/face proofs, hero freezes, and promotion/closeout gates.
- Barcelona absorption and cadastre/source-shape work lands, including `2025_IRIS_Peticions_Ciutadanes_OpenData (1).xml`.
- Main platform Track 1/Track 2 work begins late: event fabric D1, perception candidate event D1, SUMO simulation D1, integrated event/perception/SUMO smoke, flow consumption, oracle bridge, flowpack cleanup, promotion gate runner/batch.

The certified state document says Platform v1 is a review-only snapshot, not a production/autonomous/control system. That boundary stays load-bearing in later gates.

### 2026-06-29 early: Handover milestone after D2/R5

The workspace packages two handovers:

- `CITYBRAIN_NEW_CONVERSATION_HANDOVER_CONSOLIDATED_2026-06-29.md`
- `CITYBRAIN_FULL_PROJECT_HANDOVER_CONSOLIDATED_2026-06-29_v2.md`

The full handover records:

- Track 1 D2 closeout completed with `PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS`.
- Track 2 closed through R5 evidence refinement.
- Recommended next task: `MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`.
- Strict claim boundaries: no production readiness, dispatch, enforcement, public-safety command, traffic/transit/port control, legal finding, certified impact, or autonomous monitoring.

This is a clean transfer point, but not the workspace tip.

### 2026-06-29: D3, D4, D4X, D4Y build-out

After the handover, work continues heavily:

- D3: Event Fabric service hardening and multicity adapters, Perception D3 DeepStream bridge/preflight/review API, SUMO D3 network extraction/scenario catalog, integrated service smoke, D3 closeout.
- D4: Omniverse/3D subset preflight, USD city subset binding, control-room experience preflight, review UI, event feed/overlay, evidence trace, scenario replay, briefing panel, trace/persona experience, integration smoke, closeout and D5 roadmap.
- D4 3D/asset line: Barcelona asset pipeline, four-layer USD preview, load prep, city asset contract, visual mesh/footprint alignment, NYC scene probes/exportability/full I3S export, Barcelona LOD2 full I3S export.
- D4X/Track2C product/demo line: control room app shell, NYC live city app, app UX redesign, demo capture, rich content integration, dashboard data integration, city story compiler/dashboard, city episode pack, first episode app rebuild, Omniverse viewport bridge.
- D4Y intelligence/orchestration line: city situation model/runtime binding, situation graph/query, evidence-bound QA/narrator, intelligence substrate closeout, R2 orchestration fabric/router/harness/adapter contracts, R3 live orchestrator runtime slice and insight engine slice, R3 closeout.

The lineage has now shifted from "prove data/graph/query" to "harden a bounded runtime and product/operator experience while preserving review-only boundaries."

### 2026-06-30: D4Y/R7 through D6 local product lanes

The day started with D4Y runtime hardening and CER/SEG shared-contract smoke, then moved much further:

- R5/R6 domain and incident/event proofs closed, including first-two-domain proof and incident-event mode.
- Track2A/Track2B/Track2C advanced Omniverse/product bridge work: city asset contracts, city episode packs, viewport/camera bridge, object picking, USD-to-CER bridge, Kit selection, asset binding, Kit/Composer handoff, and event overlay integration.
- D6 control-room work moved from preflight into reference demo R1, R2 polish, R7 relationship overlay integration, event-context overlay integration R4, and closeout refresh R2.
- R7/R8 relationship work advanced from source-diverse edge seed R2 to runtime preflight/slice and R8 hardening. R7 R2 accepted 28 new grounded edges across 7 source families with max source-family share 0.1429; R8 hardened 133 review-context edges.
- Domain packs expanded through mobility, building compliance, property planning, and city asset identity. City Asset Identity R7 closeout accepted 20 grounded review-context edges.
- D5/D6 local-running work closed the local served runtime -> event fabric -> Track2 handoff -> running control-room slice path.
- Incident Mode closed a local/replay lane through evidence bundle R1, operator review R2, runtime smoke R3, closeout, and Track2A operator-surface handoff R4.
- Hero Neighbourhood closed a scene-pack lane: twin preflight, asset binding R1, event overlay R2, Kit/Composer handoff R3, and scene-pack closeout.
- CER/SEG v2 closed a contract/generalization lane: cross-city preflight, canonical entity contract R1, relationship ontology R2, confidence/review-state contract R3, runtime bridge smoke R4, and cross-city v2 closeout.
- Hero Neighbourhood control-room reference demo R1 then turned the readiness-reviewed lane into a green operator-facing artifact package: 45 manifest rows, 8 Hero bindings, 8 Hero overlays, 6 operator-surface packets, 6 web companion packets, 21 unresolved/quarantined preserved refs, 0 blocking gaps, and 3 non-blocking gaps.
- Demo R1 closeout and milestone freeze preserved that package as a bounded local/replay milestone.
- Track D closed and froze HITL reviewed action as a proposal-only governance spine: human review states, guardrail smoke, audit trail, and inert execution adapter stub only.
- Track A closed and froze the real USD twin proof: local/replay footprint-like USDA, graph-to-USD status overlay, replay route animation, and no certified geometry or production Omniverse claim.
- Track P closed the product packaging/persona/collateral lane with 25 collateral artifacts, 4 personas, claim labels, capture readiness, and packaging-only boundaries.
- Hero USD Twin + HITL integration readiness proved Track A and Track D could align without crossing boundaries, then R2 composed the USD twin, HITL reviewed-action, persona, route animation, operator surface, and web companion context into a green demo package. R2 closeout audited that package, milestone freeze froze it, Collateral R2 packaged it for review, final package review reconciled the outward package, and certified-state/handover refresh consolidated the decision ledger.

The observed tip is now:

```text
MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH
PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS
required upstreams: 6/6
optional upstreams: 15/15
closed tracks: 20
deferred tracks: 11
ready next tracks: 5
stale recommendation detection: PASS
blocking gaps: 0
non-blocking gaps: 3
next recommended task: MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT
```

The lineage has now shifted from "components exist and can interoperate" to "bounded product lanes can be composed into an operator-facing local/replay control-room story" and, for Hero Neighbourhood, into a frozen and packaged R2 state. The certified-state refresh now makes the next decision explicit: define the reviewed option-set contract before runtime expansion.

## Lineage map

```text
RTX / CityBrain vision
  -> source catalog and city/data strategy
  -> NYC base data + PLUTO/MapPLUTO + schema v1
  -> A4 graph projection and gates
  -> A5 deterministic evidence/query/narration
  -> A6 cuOpt review optimization
  -> A8 face/map/route operating surface
  -> A9/G1 board reconciliation
  -> London second-city core D4-D13c
  -> NYC Flow 3 + Chicago + Barcelona + Singapore scout
  -> FlowX/XData cross-city expansion and review-flow acceptance
  -> PV1 review-only snapshot D3-D22
  -> Track 2 FlowPack/oracle/promotion closure through R5
  -> Track 1 runtime/body D1 and D2 closeout
  -> D3 service hardening
  -> D4 product/operator/3D/control-room layer
  -> D4X app/demo/episode/viewport work
  -> D4Y orchestration, insight, runtime, CER/SEG contract hardening
  -> R7/R8 source-diverse relationship registry and runtime slices
  -> D5/D6 local-running control-room slice
  -> D6 Incident Mode
  -> Track2A D5 Hero Neighbourhood scene pack
  -> D6 CER/SEG cross-city v2 contract/generalization lane
  -> Hero Neighbourhood + CER/SEG v2 integration-readiness review
  -> Hero Neighbourhood control-room reference demo R1
  -> Demo R1 closeout and freeze
  -> Track D HITL reviewed-action governance spine
  -> Track A real USD twin spatial proof
  -> Track P product packaging/persona/collateral
  -> Hero USD Twin + HITL integration-readiness review
  -> Hero USD Twin HITL control-room demo R2
  -> Hero USD Twin HITL control-room demo closeout R2
  -> Hero USD Twin HITL control-room demo milestone freeze R2
  -> Collateral R2 after Track A and Track D
  -> Hero USD Twin HITL final package review
  -> R2 certified-state and handover refresh
```

## Artifact families

### Control and handover docs

The `TXRCityBrain_*` and `CITYBRAIN_*HANDOVER*` files are the human control plane. They summarize what is certified, what is planned, and what cannot be claimed. The most important stale-boundary correction is that June 29 handover docs predate the later D3/D4/D4Y work.

### Runner scripts

The `scripts/run_*.py` and top-level `txr_citybrain_*.py` files are the implementation lineage. Naming is chronological and gate-oriented:

- `a*`: early NYC graph/query/narration/map line.
- `lon_*`: London Flow 2 and later London flow expansion.
- `f3_nyc_*`, `chi_*`, `barc_*`, `sg_*`: city/flow cartridges.
- `pv1_*`: Platform v1 snapshot gates.
- `main_*`: main Track 1/Track 2 runtime/product/orchestration gates.
- `d4_3d_*`: 3D / USD / I3S / Omniverse asset line.

### Outputs

The `outputs` directory is the real versioned ledger. Each output root is an immutable-ish task record with decision files, reports, hashes, audits, and often copied artifacts. The no-mutation pattern is repeated throughout the later gates and is central to the workspace's lineage model.

### Data

The data layer includes local and landed sources for NYC, London, Chicago, Barcelona, and other scouts. Large data files are evidence inputs, not authored project code. Examples include PLUTO/MapPLUTO, FDNY incident response, NYC vehicle collisions, OS Open TOID, London/Barcelona landing packs, and the multi-city `data_landing` roots.

## Current state to continue from

Continue from:

```text
MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH
PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS
```

Recommended next task from the latest decision:

```text
MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT
```

Important current lane states:

```text
R2 certified state and handover refresh:
PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS

Hero USD Twin HITL final package review:
PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS

Collateral R2:
PASS_COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_WITH_LIMITATIONS

Hero USD Twin HITL milestone freeze R2:
PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_WITH_LIMITATIONS

Hero USD Twin HITL demo closeout R2:
PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS

Hero USD Twin HITL demo R2:
PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS

Hero USD Twin + HITL integration readiness:
PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS

Track A real USD twin:
PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS

Track D HITL reviewed action:
PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS

Track P product packaging:
PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS

Hero Neighbourhood control-room demo:
PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS

Hero/CERSEG integration readiness:
PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS

Hero scene pack:
PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS

CER/SEG v2:
PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS

Incident Mode Track2A handoff:
PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS

D5/D6 local-running slice:
PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS

R8 relationship hardening:
PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS
```

The R2 certified-state refresh reported 6/6 required upstreams found, 15/15 optional upstreams found, 20 closed tracks, 11 deferred tracks, 5 ready next tracks, JSON parse pass, frozen-facts reconciliation pass, stale recommendation detection pass, 0 blocking gaps, 3 non-blocking gaps, and no production/public/API/live-monitoring/autonomous/dispatch/control/enforcement/legal/certified/citywide-twin/physical-accuracy/automated-action claim.

## Claim boundaries that survived the lineage

Across the project, the durable boundary is:

- review/context only, not production.
- candidate/review for perception-like events, not identity/biometric/legal determination.
- simulated/context for SUMO/synthetic outputs, not observed truth or certified traffic model.
- no dispatch, enforcement, routing/control, public-safety command, legal finding, health determination, certified impact, or autonomous monitoring.
- LLM/NIM narration is bounded by deterministic evidence and grounding gates.

That boundary is not decoration; it is the main invariant connecting early architecture docs, PV1, Track 1 D2/D3/D4, D4Y, R7/R8, D5/D6 local-running, Incident Mode, Hero Neighbourhood, CER/SEG v2, HITL reviewed action, real USD twin proof, product packaging, final package review, and the latest R2 certified-state/handover refresh.

## Practical note

Git now preserves a small script/document baseline through `1b3a881`, but generated outputs and large data remain intentionally out of Git. Preserving lineage still depends on the additive output roots, decision JSONs, hash manifests, no-mutation audits, and chronology documents.

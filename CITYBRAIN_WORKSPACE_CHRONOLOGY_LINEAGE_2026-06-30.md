# CityBrain Workspace Chronology and Lineage

Generated: 2026-06-30
Workspace: `C:\Users\hazem\Documents\CityBrain`

## Executive read

This workspace has no usable Git history yet: the repository is initialized on `master`, but there are no commits and almost everything is untracked. The lineage is therefore encoded in filesystem timestamps, additive runner/output pairs, handover packs, manifests, and decision JSON files.

The project evolved from RTX/CityBrain vision documents into a governed city digital-twin platform with data landing, schema, graph, query/narration, web face/map surfaces, multi-city FlowPacks, Platform v1 review-only gates, Track 1 runtime gates, D4 operator/product/3D work, and finally D4Y orchestration/runtime/contract hardening.

The latest observed workspace tip is:

```text
outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke
PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_WITH_LIMITATIONS
timestamp: 2026-06-29T23:26:57+00:00
local file time: 2026-06-30 00:26:57
next main Track 1 task: MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE
parked D5 task: PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
```

Important nuance: `CITYBRAIN_FULL_PROJECT_HANDOVER_CONSOLIDATED_2026-06-29_v2.md` is a real handover milestone, but it is not the final workspace state. It records the project after Track 1 D2 closeout / Track 2 R5, while later files on 2026-06-29 and 2026-06-30 show D3, D4, D4X, D4Y, and Track2B/Track2C work continuing.

## Workspace evidence base

- Git: initialized, no commits; `git status` reports `No commits yet on master`.
- Top-level scale:
  - `outputs`: 96,369 files, about 24.1 GB, latest 2026-06-30 00:24-00:26.
  - `scripts`: 381 runner/helper scripts, latest 2026-06-30 00:24.
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

### 2026-06-30 00:25-00:26 local: current tip

Two latest gates define the observed tip:

1. `outputs/main_track1_d4y_r4_live_runtime_hardening`
   - Status: `PASS_MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_WITH_LIMITATIONS`
   - Mode: local runtime hardening only.
   - Explicit non-claims: no production runtime, no public API, no live agents, no external LLM, no app integration, no domain-pack runtime, no production CER/SEG, no command/control/enforcement/routing.
   - Recommended next Track 1 task at that point: `MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE`.

2. `outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke`
   - Status: `PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_WITH_LIMITATIONS`
   - Purpose: contract-level smoke/alignment for CER/SEG shared contracts.
   - Explicit non-claims: no production CER, no production SEG, no graph database runtime, no traversal service, no domain-pack runtime, no app integration, no public API, no live agents, no external LLM.
   - No mutation: watched prior D4/D4Y/Track2 roots unchanged.
   - Recommended next main Track 1 task: `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE`.

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
MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE
PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_WITH_LIMITATIONS
```

Recommended next main Track 1 task from the latest decision:

```text
MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE
```

Parallel recommendations from the same latest decision:

```text
Track2A: D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1
Track2B: MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed
Track2C: MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes
```

But some of those parallel recommendations are already partly or fully represented by later timestamped output roots, so any next run should first inspect the exact latest decision files for the relevant branch.

## Claim boundaries that survived the lineage

Across the project, the durable boundary is:

- review/context only, not production.
- candidate/review for perception-like events, not identity/biometric/legal determination.
- simulated/context for SUMO/synthetic outputs, not observed truth or certified traffic model.
- no dispatch, enforcement, routing/control, public-safety command, legal finding, health determination, certified impact, or autonomous monitoring.
- LLM/NIM narration is bounded by deterministic evidence and grounding gates.

That boundary is not decoration; it is the main invariant connecting early architecture docs, PV1, Track 1 D2/D3/D4, D4Y, and the latest CER/SEG shared-contract smoke.

## Practical note

Because Git has no commits, preserving lineage now means committing a baseline or at least snapshotting the control docs, scripts, and decision artifacts. Until then, file timestamps and additive output roots are the only historical record.

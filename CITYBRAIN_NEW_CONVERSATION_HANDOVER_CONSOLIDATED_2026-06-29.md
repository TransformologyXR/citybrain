# CityBrain / Digital Twin — New Conversation Handover

Date: 2026-06-29  
Purpose: use these files to start a fresh ChatGPT conversation inside the **Digital Twin / CityBrain** project without losing the active state.

## How to use this handover

In the new project conversation, upload or paste these documents and say:

> Read the handover docs and continue from the current state. Do not re-litigate completed gates. First confirm the active queue, then prepare the next Codex prompt I ask for.

The most important file to paste first is:

- `05_NEW_CHAT_BOOTSTRAP_PROMPT.md`

## Current project state in one paragraph

CityBrain has now closed the main Track 2 platform/flowpack cycle for this phase, including FlowPack cleanup, Oracle bridge recheck, promotion runner, R4 promotion batch, Chicago F2/F5 data strengthening, and R5 evidence refinement. Track 1 has advanced from D1 proofs to a bounded D2 runtime: Event Fabric D2, Perception D2, SUMO D2, and the integrated D2 runtime smoke are all green, with one expected limitation carried forward from SUMO D2: Barcelona traffic-section coordinates were used as a bounded SUMO-routeable equivalent, not a complete certified routable street graph.

## Active next task

```text
MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP
```

This is a closeout/freeze and roadmap gate only. It must not start D3 work.

## Immediate priority

Use the already prepared closeout prompt from:

```text
04_NEXT_CODEX_PROMPT_TRACK1_D2_CLOSEOUT.md
```

## What is closed

### Track 2 core

```text
MAIN-PLATFORM-FLOW-CONSUMPTION-CONTRACT-D1 = PASS_WITH_LIMITATIONS, then cleaned
MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1 = PASS_WITH_LIMITATIONS, then rechecked clean
MAIN-PLATFORM-FLOWPACK-LIMITATION-CLEANUP-R1 = PASS
MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1 = PASS
MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1 = PASS
CHI-F2X-F5X-DATA-STRENGTHENING-R1 = PASS
CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1 = PASS
```

Track 2 is closed for this cycle unless control-doc reconciliation is needed.

### Track 1 D2 runtime

```text
MAIN-EVENT-FABRIC-D2 = PASS
MAIN-PERCEPTION-D2 = PASS
MAIN-SUMO-D2 = PASS_WITH_LIMITATIONS
MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE = PASS_WITH_LIMITATIONS
```

Track 1 D2 is functionally proven. It still needs the closeout/freeze task.

## Core guardrails to preserve

Do not mutate:
- D1 outputs
- D2 producer outputs
- PV1 D19-D22
- A9/G1 snapshot outputs
- generated platform state
- accepted flow state
- city data landing/prep outputs
- R2/R3/R4/R5 artifacts unless explicitly creating an additive update under a new output root

Never claim:
- production-ready
- autonomous monitoring
- confirmed violation
- identity/biometric recognition
- dispatch recommendation
- enforcement recommendation
- public-safety command
- health determination
- routing recommendation
- traffic/transit/port control
- certified impact
- certified affected asset/building

## Handover file list

1. `01_START_HERE.md` — this file.
2. `02_TRACK1_D2_RUNTIME_STATUS.md` — Track 1 D2 status and closeout target.
3. `03_TRACK2_PARALLEL_FLOWPACK_STATUS.md` — Track 2 / FlowPack / R4/R5 status.
4. `04_NEXT_CODEX_PROMPT_TRACK1_D2_CLOSEOUT.md` — paste-ready Codex prompt for the next task.
5. `05_NEW_CHAT_BOOTSTRAP_PROMPT.md` — paste this into the new ChatGPT conversation.
6. `06_STATE_LEDGER.json` — machine-readable state ledger.
7. `MANIFEST.json` — file hashes and packaging metadata.


---

# Track 1 D2 Runtime Status Handover

## Current status

Track 1 D2 has been functionally proven. The only remaining task is closeout/freeze plus D3 roadmap.

```text
MAIN-EVENT-FABRIC-D2 = PASS_MAIN_EVENT_FABRIC_D2
MAIN-PERCEPTION-D2 = PASS_MAIN_PERCEPTION_D2
MAIN-SUMO-D2 = PASS_MAIN_SUMO_D2_WITH_LIMITATIONS
MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE = PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS
```

## D2 accepted close sentence

```text
CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.
```

## Event Fabric D2

Status:

```text
PASS_MAIN_EVENT_FABRIC_D2
```

D2 role:
- runtime substrate for bounded live/polled events
- durable cursors
- idempotent append
- dedupe keys
- current-state materialization
- current-state API smoke
- replay-from-cursor
- EvidenceBundle smoke
- producer compatibility for Perception D2 and SUMO D2

Known key integration result from D2 integrated smoke:
- Event Fabric D2 contributed 45 events to the unified D2 smoke.
- observed/context lifecycle remained separated from candidate and simulated events.

## Perception D2

Status:

```text
PASS_MAIN_PERCEPTION_D2
```

Output root:

```text
outputs/main_perception_d2
```

Runner:

```text
scripts/run_main_perception_d2.py
```

Key results:
- Event Fabric D2 dependency verified.
- D1 deterministic fixture lane preserved with 37 D1 observations.
- Sample-media lane passed using local read-only clips from:
  ```text
  cascade_clips_manifest_and_downloader/cascade_clips/
  ```
- 47 detection observations.
- 22 candidate events, including 6 sample-media candidate events.
- 22 Event Fabric D2-compatible envelopes.
- 22 human-review packets.
- Isolated overlay append passed with 22 duplicate/idempotency hits.
- Current-state DuckDB created and populated.
- 3 replay scenarios passed.
- EvidenceBundle smoke, negative tests, claim-boundary audit, no-mutation audit, secret audit, and hashes all passed.

Limitation:
- `ffprobe` unavailable; video metadata marked `metadata_limited_ffprobe_unavailable`.
- This is accepted for D2 because sample-media assets existed and deterministic fallback detection JSON was generated.
- Perception D2 is not production CCTV, identity inference, biometric recognition, or violation determination.

## SUMO D2

Status:

```text
PASS_MAIN_SUMO_D2_WITH_LIMITATIONS
```

Output root:

```text
outputs/main_sumo_d2
```

Runner:

```text
scripts/run_main_sumo_d2.py
```

Key results:
- Native SUMO 1.27.1 ran three scenarios:
  - baseline
  - slowdown disruption
  - recovery
- Network: 30 nodes, 68 edges.
- Produced 1,200 observations.
- Produced 24 simulation events.
- Produced 24 Event Fabric D2-compatible envelopes.
- Overlay append/current state passed without mutating Event Fabric D2.
- Replay, EvidenceBundle smoke, negative tests, claim-boundary audit, no-mutation audit, secret audit, and raw TMB key scan passed.

Accepted limitation:
- Barcelona traffic-section geometry was usable and city-derived, but it is point-chain context, not a complete routable street graph.
- A bounded SUMO-routeable equivalent was generated from official Barcelona traffic-section coordinates.
- This must remain surfaced as an accepted D2 limitation.
- SUMO D2 is simulated/context-only, not traffic control, not routing recommendation, and not a certified impact model.

## Integrated D2 runtime smoke

Status:

```text
PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS
```

Output root:

```text
outputs/main_track1_d2_integrated_runtime_smoke
```

Runner:

```text
scripts/run_main_track1_d2_integrated_runtime_smoke.py
```

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

Why integrated D2 is `WITH_LIMITATIONS`:
- The SUMO D2 Barcelona routeable-equivalent limitation remains active and must be preserved.

## Remaining Track 1 D2 task

```text
MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP
```

Purpose:
- freeze Track 1 D2 certified state
- build capability ledger
- build limitations register
- build evidence index
- preserve claim boundary
- define D3 roadmap and backlog
- do not start D3 implementation

Expected status:

```text
PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS
```

Use `WITH_LIMITATIONS` because the SUMO D2 routeable-equivalent limitation remains valid and should be carried forward.

## D3 concept

D3 should mean:

```text
runtime hardening + city expansion + service/API readiness
```

Recommended D3 workstreams:
1. `MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`
2. `MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS`
3. `MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE`
4. `MAIN-PERCEPTION-D3-REVIEW-API`
5. `MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING`
6. `MAIN-SUMO-D3-SCENARIO-CATALOG`
7. `MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE`

D3 is not D4 Omniverse/product/control-room work and not D5 production/enterprise deployment.


---

# Track 2 / FlowPack / Promotion Status Handover

## Current status

Track 2 core is closed for this cycle.

```text
MAIN-PLATFORM-FLOW-CONSUMPTION-CONTRACT-D1 = PASS_WITH_LIMITATIONS, later cleaned
MAIN-PLATFORM-ORACLE-FLOWPACK-BRIDGE-D1 = PASS_WITH_LIMITATIONS, later rechecked clean
MAIN-PLATFORM-FLOWPACK-LIMITATION-CLEANUP-R1 = PASS
MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1 = PASS
MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1 = PASS
CHI-F2X-F5X-DATA-STRENGTHENING-R1 = PASS
CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1 = PASS
```

No urgent Track 2 infrastructure task remains.

## FlowPack limitation cleanup

Task:

```text
MAIN-PLATFORM-FLOWPACK-LIMITATION-CLEANUP-R1
```

Status:

```text
PASS_MAIN_PLATFORM_FLOWPACK_LIMITATION_CLEANUP_R1
```

Output root:

```text
outputs/main_platform_flowpack_limitation_cleanup_r1
```

Key cleaned results:
- NYC: `LOADED`, canonical JSONL smoke pack created with 175 rows.
- BARC: `LOADED`, active `source_view_errors = 0`; Bicing GBFS repaired into DuckDB from local raw JSON with 541 station info rows and 541 station status rows.
- CHI: `LOADED`, canonical root created at:
  ```text
  outputs/chi_allflows_consumption_prep_r1/
  ```
  JSONL smoke pack created with 175 rows.
- LON: `LOADED`, regression clean.

Oracle recheck:
- `PASS_MAIN_PLATFORM_ORACLE_FLOWPACK_BRIDGE_D1_RECHECK`
- 12 smoke queries pass.
- London `pytz` fallback removed by bounded metadata/count queries.
- Barcelona intentional missing-view test reclassified as `PASS_EXPECTED_MISSING_VIEW_REPORTED`.
- No active oracle runtime limitations remain.

## Promotion gate runner

Task:

```text
MAIN-PLATFORM-FLOW-PROMOTION-GATE-RUNNER-D1
```

Status:

```text
PASS_MAIN_PLATFORM_FLOW_PROMOTION_GATE_RUNNER_D1
```

Output root:

```text
outputs/main_platform_flow_promotion_gate_runner_d1
```

Dry-run evaluated 9 flows:
- No-op / already accepted or mounted:
  - `NYC-F2`
  - `NYC-F5`
  - `LON-F3`
  - `LON-F4`
  - `LON-F5`
  - `CHI-F7`
- Promotable dry-run drafts:
  - `LON-F7`
  - `CHI-F2`
  - `CHI-F5`

Patch drafts and R4 addendum drafts were created as dry-run only.

## Promotion batch R1

Task:

```text
MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1
```

Status:

```text
PASS_MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1
```

Applied additively:
- `LON-F7X` → `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- `CHI-F2X` → `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `CHI-F5X` → `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`
- `PV1-SNAPSHOT-ADDENDUM-R4` → `PASS_PV1_SNAPSHOT_ADDENDUM_R4`

Audits:
- Resolver/oracle recheck: `PASS`
- No-mutation: `PASS`
- Claim boundary: `PASS`
- Negative tests: `PASS`
- Secret scan: `PASS`
- Raw key scan: no hits

No-op flows were used only as regression checks and stayed unchanged. Barcelona F1-F7 stayed unchanged. PV1 D19-D22 and A9/G1 stayed unchanged.

## Newly accepted / refined flow limitations

### LON-F7X

Status:

```text
ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
```

Boundary:
- review/context only
- no enforcement
- no health determination
- no policing determination
- no public-safety command
- no operational determination

### CHI-F2X

Status:

```text
ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS
```

Boundary:
- planning/compliance context only
- no official compliance determination
- no enforcement recommendation
- person-level or sensitive sources remain review-only or aggregate/context only

### CHI-F5X

Status:

```text
ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS
```

Boundary:
- climate/asset-risk screening context only
- no engineering determination
- no health determination
- no utility-control determination
- no certified affected-building/asset determination

## Chicago F2/F5 data strengthening

Task:

```text
CHI-F2X-F5X-DATA-STRENGTHENING-R1
```

Status:

```text
PASS_CHI_F2X_F5X_DATA_STRENGTHENING_R1
```

Output root:

```text
outputs/chi_f2x_f5x_data_strengthening_r1
```

Created additive strengthened overlay mart:

```text
CHI_F2X_F5X_STRENGTHENED_MART.duckdb
```

Added:
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
- F2 now weights parcels, buildings, permits, violations, and zoning above business licenses.
- F5 now weights Open Air, green infrastructure, environmental context, and targeted 311 above broad bounded 311.
- Generated:
  - 20 strengthened F2 EvidenceBundles
  - 20 strengthened F5 EvidenceBundles
  - 25 F2 smoke queries
  - 25 F5 smoke queries
  - 10 F2 negative tests
  - 10 F5 negative tests

No platform promotion was run and no accepted status changed.

## Chicago R5 evidence refinement

Task:

```text
CHI-F2X-F5X-RECHECK-FOR-R5-ADDENDUM-R1
```

Status:

```text
PASS_CHI_F2X_F5X_RECHECK_FOR_R5_ADDENDUM_R1
```

R5 addendum status:

```text
PASS_PV1_SNAPSHOT_ADDENDUM_R5_CHI_F2X_F5X_EVIDENCE_REFINEMENT
```

Output root:

```text
outputs/chi_f2x_f5x_recheck_for_r5_addendum_r1
```

Key result:
- `CHI-F2X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`.
- `CHI-F5X` remains `ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS`.
- No promotion gate run.
- No platform state applied in place.
- R4 remains valid.
- R5 only refines evidence/source-weighting basis.

Audits:
- EvidenceBundle audit: `PASS`
- Smoke query audit: `PASS`
- Negative tests: `PASS`
- Claim boundary audit: `PASS`
- No-mutation audit: `PASS`
- Secret audit: `PASS`

## Track 2 remaining work

None urgent.

Optional later:
- Control-doc reconciliation to reflect R4/R5 in Mission Control / Current Certified State / Platform v1 DoD.
- Future city-flow strengthening only if a specific limitation becomes important.

Do not reopen Track 2 infrastructure unless there is a new concrete blocker.


---

# Paste-Ready Codex Prompt — MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP

```text
MAIN CODEX TASK — TRACK 1 D2 CLOSEOUT AND D3 ROADMAP

You are Main Codex for the CityBrain platform spine.

Task name:
MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP

Track:
Track 1 D2 — bounded runtime/body layer closeout.

Goal:
Freeze and certify the completed Track 1 D2 runtime capability, summarize exactly what is now proven, preserve limitations, and define the D3 roadmap.

This task is a closeout and roadmap gate. It must not start D3 implementation.

Current Track 1 D2 status:
- MAIN-EVENT-FABRIC-D2 = PASS_MAIN_EVENT_FABRIC_D2
- MAIN-PERCEPTION-D2 = PASS_MAIN_PERCEPTION_D2
- MAIN-SUMO-D2 = PASS_MAIN_SUMO_D2_WITH_LIMITATIONS
- MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE = PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS

D2 accepted close sentence:
CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.

Known D2 limitation to preserve:
SUMO D2 uses Barcelona city-derived traffic-section coordinates as a bounded SUMO-routeable equivalent. It is not a complete routable street graph, not a certified traffic model, and not a routing/control system.

Do not:
- mutate Event Fabric D2 outputs
- mutate Perception D2 outputs
- mutate SUMO D2 outputs
- mutate D2 integrated runtime smoke outputs
- mutate D1 outputs
- mutate PV1 D19-D22
- mutate A9/G1
- mutate generated platform state
- mutate accepted flow state
- mutate city data landing/prep outputs
- run flow-promotion gates
- start Event Fabric D3
- start Perception D3
- start SUMO D3
- start D4 / Omniverse work
- make production-ready claims
- create enforcement, dispatch, health, public-safety, routing-control, traffic-control, transit-control, port-control, or certified affected-asset claims

Output root:
outputs/main_track1_d2_closeout_and_d3_roadmap/

Required artifacts:
- README.md
- MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP.md
- MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json
- TRACK1_D2_CERTIFIED_STATE.md
- TRACK1_D2_CAPABILITY_LEDGER.json
- TRACK1_D2_LIMITATIONS_REGISTER.md
- TRACK1_D2_INPUT_ARTIFACT_AUDIT.md
- TRACK1_D2_EVIDENCE_INDEX.json
- TRACK1_D2_CLAIM_BOUNDARY.md
- TRACK1_D2_NO_MUTATION_AUDIT.md
- TRACK1_D2_SECRET_REDACTION_AUDIT.md
- TRACK1_D2_D3_ROADMAP.md
- TRACK1_D3_TASK_BACKLOG.json
- TRACK1_D3_NON_GOALS.md
- TRACK1_D4_PLACEHOLDER_NOTE.md
- hashes.sha256
- runner: scripts/run_main_track1_d2_closeout_and_d3_roadmap.py

Phase 1 — audit D2 input artifacts:
Read and verify Event Fabric D2, Perception D2, SUMO D2, and integrated D2 smoke decisions and evidence artifacts. Produce TRACK1_D2_INPUT_ARTIFACT_AUDIT.md. Confirm all four D2 gates exist, statuses are valid, limitations are surfaced, and no input root is modified.

Phase 2 — certified D2 state:
Create TRACK1_D2_CERTIFIED_STATE.md. State exactly what D2 proves:
- bounded live/polled event ingestion
- durable cursor/idempotent append path
- current-state materialization
- current-state API smoke
- perception candidate bridge
- local sample-media lane
- human-review packets
- SUMO city-derived simulation producer
- unified runtime smoke
- replay
- deterministic EvidenceBundle smoke
- separated observed/context, candidate/review, and simulated/context boundaries

Also state what D2 does not prove:
- not production real-time streaming
- not autonomous monitoring
- not production CCTV
- not identity/biometric recognition
- not traffic control
- not routing recommendation
- not certified simulation
- not public-safety command
- not dispatch
- not enforcement
- not health determination
- not certified affected-building/asset determination

Phase 3 — capability ledger:
Create TRACK1_D2_CAPABILITY_LEDGER.json with entries:
event_fabric_d2_runtime_substrate, durable_cursors, idempotent_append, current_state_api_smoke, replay_from_cursor, perception_candidate_bridge, sample_media_detection_contract, human_review_packets, sumo_city_derived_simulation_producer, sumo_bounded_routeable_equivalent, unified_d2_event_log, unified_d2_current_state, unified_d2_replay, unified_d2_evidencebundle_smoke.

Each entry needs capability_id, status, source_gate, evidence_refs, limitations, claim_boundary, next_hardening_needed, schema_version.

Phase 4 — limitations register:
Create TRACK1_D2_LIMITATIONS_REGISTER.md. Required limitations:
1. SUMO Barcelona routeable equivalent: official traffic-section coordinates are city-derived point-chain context, not full routable street graph; connector edges do not imply real turn permissions; simulated/context-only; not certified and no action taken.
2. Perception metadata: ffprobe unavailable; video metadata limited; sample-media lane passed through deterministic fallback detection JSON; not production CCTV.
3. Event Fabric D2: bounded polling/runtime smoke; no heavy streaming infra; no daemonized production service; not production real-time monitoring.
4. Integrated D2: proves integration, not production deployment; API smoke is bounded; no operational commands.

Classify each as ACCEPTED_D2_BOUNDARY, D3_HARDENING_CANDIDATE, D4_PRODUCTIZATION_CANDIDATE, or DO_NOT_REMOVE_WITHOUT_GOVERNANCE.

Phase 5 — evidence index:
Create TRACK1_D2_EVIDENCE_INDEX.json indexing decision JSONs, event logs, current-state DuckDBs, replay reports, EvidenceBundle reports, negative tests, claim-boundary audits, no-mutation audits, secret audits, and hashes.

Phase 6 — claim boundary:
Create TRACK1_D2_CLAIM_BOUNDARY.md with allowed and forbidden claims. Allowed: bounded runtime proof, governed event fabric, live/polled event smoke, perception candidate review bridge, sample-media candidate bridge, SUMO simulated mobility context, current-state API smoke, replay smoke, EvidenceBundle smoke, review/context/simulated separation. Forbidden: production-ready, autonomous monitoring, confirmed violation, identity/biometric, dispatch, enforcement, public-safety, health, routing, traffic-control, transit-control, port/vessel-control, certified impact, certified affected asset/building.

Phase 7 — no-mutation audit:
Create TRACK1_D2_NO_MUTATION_AUDIT.md proving D1 roots, D2 roots, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, city landing/prep roots unchanged; no flow promotion, no downloads, no D3 implementation.

Phase 8 — secret audit:
Create TRACK1_D2_SECRET_REDACTION_AUDIT.md.

Phase 9 — D3 roadmap:
Create TRACK1_D2_D3_ROADMAP.md. D3 theme: harden bounded D2 runtime into a service-grade multi-city runtime twin. Define but do not start:
1. MAIN-EVENT-FABRIC-D3 — service mode, stronger API contract, multi-city adapters, observability, cursor recovery, retention policy, replay API hardening.
2. MAIN-PERCEPTION-D3 — DeepStream/Metropolis on 4070, model-output adapter, real sample camera/video pipeline, stronger camera/zone governance, review API/UI integration, metadata hardening, privacy/redaction.
3. MAIN-SUMO-D3 — better network extraction beyond point-chain routeable equivalent, larger city subsets, scenario catalog, calibration against observed mobility signals, compare simulated vs observed mobility context.
4. MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE — unified runtime API, durable multi-producer service smoke, trace/debug tooling, EvidenceBundle/briefing integration, dashboard/control-room readiness.

Phase 10 — D3 backlog:
Create TRACK1_D3_TASK_BACKLOG.json with:
- MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING
- MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS
- MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE
- MAIN-PERCEPTION-D3-REVIEW-API
- MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING
- MAIN-SUMO-D3-SCENARIO-CATALOG
- MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE

Each task needs goal, prerequisites, inputs, outputs, success criteria, risks, non-goals, suggested order.

Recommended D3 order:
1. MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING
2. MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS
3. MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE
4. MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING
5. MAIN-SUMO-D3-SCENARIO-CATALOG
6. MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE

Phase 11 — D3 non-goals:
Create TRACK1_D3_NON_GOALS.md. D3 is not D4 Omniverse/control-room product experience, D5 production deployment, autonomous control, public safety system, enforcement system, certified traffic model, certified asset-risk model, production CCTV, or identity/biometric system.

Phase 12 — D4 placeholder:
Create TRACK1_D4_PLACEHOLDER_NOTE.md defining D4 as future product/3D/operator twin integration: Omniverse/OpenUSD scene integration, 3D city subset linked to runtime events, control-room UI, scenario playback in 3D, human-review workflows, trace/dashboard/briefing experience, demo/product packaging. Do not create D4 tasks.

Phase 13 — hashes:
Create hashes.sha256.

Phase 14 — final decision:
Create MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json.

Allowed statuses:
- PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP
- PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS
- FAIL_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP

Expected final wording:
PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS

Use WITH_LIMITATIONS because the accepted SUMO D2 routeable-equivalent limitation remains active and should be carried forward.
```


---

# New Chat Bootstrap Prompt — CityBrain / Digital Twin Project

Paste this into the new ChatGPT project conversation after uploading these handover docs.

```text
You are continuing the CityBrain / Digital Twin project from the attached handover docs.

Read these first:
1. 01_START_HERE.md
2. 02_TRACK1_D2_RUNTIME_STATUS.md
3. 03_TRACK2_PARALLEL_FLOWPACK_STATUS.md
4. 04_NEXT_CODEX_PROMPT_TRACK1_D2_CLOSEOUT.md
5. 06_STATE_LEDGER.json

Treat these as the active state unless I provide newer outputs.

Do not ask me to repeat prior context unless a required artifact is missing. Do not re-litigate completed gates. The heavy prior conversation is being replaced because it became too large.

Current state:
- Track 2 core is closed for this cycle.
- Chicago R5 evidence refinement passed and did not change flow statuses.
- Track 1 D2 is functionally proven.
- Event Fabric D2 = PASS.
- Perception D2 = PASS.
- SUMO D2 = PASS_WITH_LIMITATIONS.
- Track 1 D2 integrated runtime smoke = PASS_WITH_LIMITATIONS.
- The only active next task is MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP.

Important limitation to preserve:
SUMO D2 uses Barcelona city-derived traffic-section coordinates as a bounded SUMO-routeable equivalent. It is not a complete routable street graph, not a certified traffic model, and not a routing/control system.

Start by confirming the active queue:
1. MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP
2. after that, decide D3 sequence from the closeout output

When I ask for a prompt, produce a paste-ready Codex prompt. Keep the output grounded in the handover docs and actual passed statuses.

Do not mutate or suggest mutating:
- D1 outputs
- D2 producer outputs
- PV1 D19-D22
- A9/G1
- generated platform state
- accepted flow state
- city data landing/prep outputs
- R2/R3/R4/R5 unless a new additive gate explicitly does it

Do not claim:
- production-ready
- autonomous monitoring
- confirmed violation
- identity/biometric recognition
- dispatch recommendation
- enforcement recommendation
- public-safety command
- health determination
- routing recommendation
- traffic/transit/port control
- certified impact
- certified affected asset/building
```

# TXR City Brain — Consolidated Codex/Claude Handoff (2026-06-28)

## Executive status

- **Application Snapshot v1** remains `G1_PASS`.
- **Platform v1** is now closed as a review-only platform snapshot: `PV1-D19/D20/D21/D22 GREEN · PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT`.
- D19/D20 policy is load-bearing: no LLM controls actuators, no model emits operational commands, no review route becomes control, and any future actuator-adjacent adapter requires deterministic policy bounds and a safety case.
- **Track 2** is closed and strengthened: `FLOWX-DATA-ROUTE-CATALOG-R1 + TARGETED D3-R2 GREEN · PASS_TARGETED_D3_R2_AND_DATA_ROUTE_CATALOG_R1`.
- Post-PV1 addendum R1: `FLOWX-REVIEW-FLOW-ACCEPTANCE-D1 GREEN · PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS`.
- Track 2 current status after addendum: five NYC/Chicago lanes are `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`; BARC-F7 remains `CANDIDATE_ONLY_NOT_ACCEPTED / BLOCKED_BY_CITY_CORE`; Singapore LTA remains blocked by auth.
- NYC-F1X-D3-R2 is strengthened by NYC 311 recent window `13,924,344 / 13,924,344 WINDOWED_COMPLETE`.
- CHI-F4X-D3-R2 is strengthened by Open Air individual `8,961,666 / 8,961,666 FULL` and Cook parcels `22,860,605 / 22,860,605 FULL`.
- Manual Omniverse asset preparation is external: grey-city assets and textured hero locations for the four active cities, globally geolocated where possible. Codex should not assume assets exist until a future scene-binding gate runs.

## Current decision structure

Do not reopen PV1 by default. Do not mutate the D19-D22 snapshot.

Valid next moves:

1. Product/demo/narrative pack.
2. Compliance/planning vertical depth pack.
3. Omniverse visual twin / `CITY-SCENE-BINDING-D1` once assets are ready.
4. Production review-only hardening.
5. Data moat / source freshness layer.
6. Agent/NIM/NeMo briefing layer.
7. Autonomy / operational control remains deferred as a separate safety-critical future program.


## Current Flow 3 gate ledger

```text
F3-NYC-D1   GREEN_WITH_MISSING_SOURCES
F3-NYC-D2   GREEN_WITH_BOUNDED_SAMPLE
F3-NYC-D2C  GREEN_WITH_CAPPED_WORKING_SET
F3-NYC-D3   GREEN_WITH_LOCATION_CONFIDENCE_TIERS
F3-NYC-D4   GREEN_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION
F3-NYC-D5   GREEN_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS
F3-NYC-D6   GREEN - LIVE SPARK/NIM REPLAY
F3-NYC-D7   GREEN - LIVE FACE-LAYER ROUTE/MAP/TRACE
F3-NYC-D8   GREEN - DETERMINISTIC THREE-HERO PACKAGE
F3-NYC-D9   PASS_WITH_CAPPED_SOURCE_LIMITATION - ACCEPTED FLOW 3 SNAPSHOT
F3-NYC-D9FULL PASS_WITH_FULL_SOURCE_INPUTS_AND_STAGE_LIMITATIONS
```

## Current Flow 3 source-status language

```text
Flow 3 D10FULL uses full-source D1/D2C inputs for MVC crashes, FDNY firehouses, Fire Dispatch, and EMS Dispatch.
Candidate MapPLUTO tax-lot context is not a certified affected building or affected asset.
Operator-review routes are not emergency dispatch, emergency response recommendations, or navigable routes.
FDNY, Fire Dispatch, and EMS rows without official coordinates remain source-context evidence only.
Firehouse/resource proximity is response-resource context, not dispatched-unit truth.
D10FULL does not claim final emergency operations completion or certified affected-building truth.
```

## London expansion queue

### LON-F3X-D1 — London Resilience / Fire-Incident Context Expansion
- Mount onto the accepted London Flow 2 city core.
- Add LFB incident records, LFB mobilisation records, TfL disruptions/status, London Air, and bounded EA flood/water context where relevant.
- Boundary: review-only incident / affected-context briefing; not emergency command, fire dispatch, or operational public-safety instruction.

### LON-F4X-D1 — London Mobility / Environment Expansion
- Mount onto the accepted London core.
- Add TfL Unified API arrivals/status/disruptions, London Air, existing EV/charging context, and bounded event/crowd sources if found.
- Boundary: mobility/environment context and review planning only; no public-order, crowd-control, dispatch, or emergency command claim.

### LON-F5X-D1 — London Flood / Climate Risk Context Expansion
- Mount onto the accepted London core.
- Add EA flood-monitoring API warnings/alerts/areas/water levels/flows plus London flood-risk, air/emissions/noise, and bounded energy data where available.
- Boundary: risk context, not certified infrastructure failure propagation; no utility-control or emergency-response claim.

## Singapore status

### SG-D1 — Credential-safe source/API probe
- Read `LTA_DATAMALL_API_KEY` from environment only.
- Probe LTA DataMall dynamic/static APIs, Data.gov.sg weather/air/traffic-image APIs, OneMap search/reverse geocode/routing, and any no-key government APIs.
- Emit source inventory, API status, schema samples, rate/limit notes, and no-secret logs.
- Status: scout exists, but authenticated live API proof remains blocked; do not mark Flow 4 accepted.

### SG-D2 — Singapore transport/environment cartridge ingest
- Canonicalize traffic incidents/images/bus arrivals/routes as Event / Sensor / RoadSegment / TransitNode context.
- Add weather/rainfall/air context from Data.gov.sg/NEA.
- Use OneMap for address/geospatial grounding.

### F4-SG — Crowd / transport / environment flow
- Scenario: major event or crowd surge; traffic/camera/weather/air context feeds an operator briefing and review plan.
- Boundaries: no public safety instruction, no real-time dispatch claim, no face recognition, no live legal/operational recommendation.

## Credential handling

The DataMall key must **not** be committed. Use:

```powershell
$env:LTA_DATAMALL_API_KEY = "..."
```

or a local `.env` file excluded by `.gitignore`.

## Files created in this consolidation

- `TXRCityBrain_MissionControl_consolidated.html`
- `TXRCityBrain_ToDo_consolidated.html`
- `TXRCityBrain_Codex_Claude_Handoff.md`

## Recommended immediate Codex order

1. Do not mutate PV1-D19/D20/D21/D22; it is the final review-only PV1 freeze.
2. If desired, run `FLOWX-REVIEW-FLOW-ACCEPTANCE-D1` as a post-PV1 addendum to resolve the five review-route-ready lanes blocked by acceptance policy.
3. Continue manual Omniverse grey-city / hero-location asset preparation outside Codex.
4. Choose the next post-PV1 value track based on platform gap and data strength, not breadth for breadth's sake.
5. Keep Singapore LTA/auth recovery and Barcelona city-core acceptance as explicit deferred blockers, not active assumptions.


## Post-PV1 addendum R1 — review-flow acceptance policy

```text
FLOWX-REVIEW-FLOW-ACCEPTANCE-D1  GREEN
PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS
```

This is a **post-PV1 addendum**. It does not mutate the frozen `PV1-D19/D20/D21/D22` review-only snapshot.

**Accepted review flows with limitations:**

```text
NYC-F1X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F5X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F6X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F3X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F4X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
```

**Preserved blocker:**

```text
BARC-F7  CANDIDATE_ONLY_NOT_ACCEPTED / BLOCKED_BY_CITY_CORE
```

**Boundary:** accepted review flow means governed review use only. It does **not** mean production control, autonomous operation, dispatch, public-safety instruction, traffic/transit/utility/port/airport command, enforcement, health determination, or certified affected-asset/building truth.

Verification: no-overclaim PASS, no-mutation PASS, hashes PASS; `PV1-D19/D20/D21/D22` frozen outputs unchanged.

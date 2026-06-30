# TXR City Brain — Consolidated Codex/Claude Handoff (2026-06-27)

## Executive status

- **NYC Flow 2** remains the certified spine; **A9/G1** is still the formal application snapshot gate.
- **London Flow 2** is now an accepted city core: D13C + **LON-HERO dual scenarios** are green.
- **NYC Flow 3** is accepted through D9FULL as a governed incident-response / candidate-asset / operator-review flow with full-source inputs and stage limitations.
- **Chicago Flow 1 + Flow 7** are accepted through **CHI-F1F7-D5** with capped-source limitations carried forward.
- New model: **one city = city core cartridge; each flow = sub-cartridge mounted onto that city core**.
- **London mounted expansions are green through D6**: **LON-F3X**, **LON-F4X**, and **LON-F5X** now have accepted flow-extension snapshots via `LON-FLOWX-D6`. Singapore Flow 4 remains planned but authenticated live API proof is blocked; Barcelona is a fresh city-core scout candidate.

## Consolidated board decisions

1. Keep **A9/G1** visible as the application snapshot gate.
2. Treat **NYC, London, and Chicago** as accepted city cores; do not rebuild them from zero for new flows.
3. Use `{CITY}-F{FLOW}X-D{DAY}` for mounted flow expansions. The `X` means extension on an accepted city core.
4. Treat **London** as the proven expansion core because Flow 3, Flow 4, and Flow 5 reused its accepted IDs, geography, face/NIM conventions, and limitations through D6.
5. Keep **Singapore / Flow 4** in planned status until authenticated live API proof clears. Do not treat SG-D1 as accepted Flow 4.

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

## London accepted mounted expansions

### LON-F3X - London Resilience / Fire-Incident Context Expansion
- Status: `PASS_ACCEPTED_EXTENSION_SNAPSHOT` via `LON-FLOWX-D6`.
- Output: `outputs/lon_flowx_expansion_path_d2_to_d6/`.
- Mounts onto the accepted London Flow 2 city core.
- Adds bounded LFB incident/mobilisation schema and sample landing, TfL disruptions/status, London Air, and bounded EA flood/water context where relevant.
- Boundary: review-only incident / affected-context briefing; not emergency command, fire dispatch, or operational public-safety instruction.

### LON-F4X - London Mobility / Environment Expansion
- Status: `PASS_ACCEPTED_EXTENSION_SNAPSHOT` via `LON-FLOWX-D6`.
- Mounts onto the accepted London core.
- Adds TfL status/disruptions/BikePoint, London Air, existing EV/charging context, and bounded mobility/environment source context.
- Boundary: mobility/environment context and review planning only; no public-order, crowd-control, dispatch, route guarantee, or emergency command claim.

### LON-F5X - London Flood / Climate Risk Context Expansion
- Status: `PASS_ACCEPTED_EXTENSION_SNAPSHOT` via `LON-FLOWX-D6`.
- Mounts onto the accepted London core.
- Adds EA flood-monitoring API warnings/alerts/areas/water levels/flows plus London Air and emissions discovery context.
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

1. Review/lock `LON-FLOWX-D6` accepted extension snapshot and carry it into A9/G1.
2. Resume cross-city queue with `CHI-F2X-D2`, `BARC-F4-D3` / `BARC-F7-D3`, or `NYC-F4X-D2`.
3. Keep `SG-D1` / `F4-SG` planned until authenticated live API proof clears.

# Codex Handover — Track A: The Twin, For Real

## Purpose

Build the bounded Hero Neighbourhood real-USD twin track end to end.

This is not an Omniverse polish sprint. The goal is to deepen the already-green Hero scene into a stronger spatial control-room proof:

```text
real/accepted footprint layer
→ USD/OpenUSD scene layer
→ entity/scene binding
→ graph-to-USD status overlay
→ one replay event / route animation
→ closeout
```

## Run as a separate thread

Run this package in its own Codex thread.

Do not mix it with the Track D HITL reviewed-action package. Both tracks share the same scenario contract, but they should produce separate outputs and closeouts.

## Current upstreams to consume

Consume, do not mutate:
- D6 Hero Neighbourhood Control Room Reference Demo Closeout R1
- Hero Neighbourhood Scene Pack Closeout
- Incident Mode Closeout
- Incident Mode Track2A Operator Surface Handoff R4
- CER/SEG Cross-City v2 Closeout
- Hero + CERSEG Integration Readiness Review
- R7/R8 edge registry outputs
- D6/D5 local running slice closeout

## Execution order

1. `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-PREFLIGHT`
2. `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-FOOTPRINT-USD-R1`
3. `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-GRAPH-TO-USD-STATUS-OVERLAY-R2`
4. `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REPLAY-EVENT-ROUTE-ANIMATION-R3`
5. `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-CLOSEOUT`
6. Optional freeze: `MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-MILESTONE-FREEZE`

## Non-negotiable boundaries

Do not claim:
- production Omniverse deployment
- citywide twin
- certified twin
- live monitoring
- autonomous incident detection
- alerting
- dispatch
- routing/control
- enforcement
- legal/certified conclusions
- automated action

## Output discipline

Each task should create:
- output root
- decision JSON
- local open index
- input artifact index
- validation report
- claim-boundary audit
- no-mutation audit
- secret audit
- hash manifest

## Design guardrail

The win is:

```text
real spatial object
+ canonical/scene binding
+ graph relationship
+ event/status overlay
+ evidence trace
+ operator surface
```

The win is not:
```text
make Omniverse pretty
```

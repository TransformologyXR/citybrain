# Shared Hero Scenario Contract

Use this same scenario across Track A, Track D, and later Track B so the roadmap becomes one coherent story rather than separate demos.

## Scenario ID

`HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001`

## Scenario source

Use the already-frozen Hero Neighbourhood / Incident / CERSEG / operator-surface artifacts.

Known upstream truth:
- `MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT` selected: `LON local replay scene focus / corridor event context`.
- `MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT` is green.
- `MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT` is green.
- `MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4` is green.
- `MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT` is green.
- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW` is green.
- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1` is green.

## Scenario narrative

A local/replay event indicates a bounded construction/corridor disruption in the hero neighbourhood. Treat it as a review-context replay event, not a live detected incident.

The event affects:
- one hero corridor / road segment or route context
- one or more bound hero scene assets / prims
- nearby building/site/context entities where already supported by upstream evidence
- operator-surface packets and web companion packets
- unresolved/quarantined contexts that must remain preserved

The visible story:
1. Event/context is loaded from replay/human-provided package.
2. Incident Mode contextualizes affected entities and evidence.
3. Hero scene shows spatial context and overlay state.
4. Track D creates a reviewed action proposal object for human decision, not an automated action.
5. Later Track B may use the same scenario for SUMO/Plan Mode prediction.

## Boundary

This scenario is:
- local/replay only
- human-or-replay initiated
- review/query context only
- non-certified
- not live monitoring
- not alerting
- not dispatch
- not routing/control
- not enforcement
- not legal/certified conclusion
- not an automated action system
- not a citywide certified twin

## Required preservation

Every track using this scenario must preserve:
- evidence refs
- limitation refs
- unresolved/quarantined refs
- claim labels
- review states
- source/scene refs that are not canonical IDs

Do not promote scene paths, operator refs, source refs, or prim paths into canonical entity IDs.

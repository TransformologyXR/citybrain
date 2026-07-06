# CityBrain Authoritative Strategy and Architecture Docs

Generated: 2026-07-05

This package contains the R2 canonical documentation set for CityBrain as a governed city intelligence and operations platform. R2 adds a certified-state ledger, terminology crosswalk, CHECK v0/v1 split, Event Fabric v0/v1/v2 split, and latest ASK / Metropolis / VSS / DeepStream / Omniverse status updates.

## Documents

1. `01_CITYBRAIN_PRODUCT_DEFINITION_AND_VISION.md`  
   Product thesis, authority model, users, current state, and north-star loop.

2. `02_CITYBRAIN_INTELLIGENCE_MODES_CAPABILITY_MAP.md`  
   Detailed capability map for all intelligence modes: purpose, calculation, data needs, maturity, gaps, and roadmap.

3. `03_CITYBRAIN_AGENTIC_INTELLIGENCE_LAYER.md`  
   Defines background and task agents, agent run envelope, authority levels, agent-to-mode mapping, and orchestration rules.

4. `04_CITYBRAIN_ARCHITECTURE_AND_ROADMAP.md`  
   Architecture layers, current state, main gaps, and phased roadmap from prototype spine to governed operations platform.

5. `05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md`  
   Implementation-facing packet contracts, entity spec format, source classes, authority envelopes, event/perception/spatial handoff contracts, and validation rules.

6. `06_CITYBRAIN_CERTIFIED_STATE_LEDGER_AND_TERMINOLOGY_CROSSWALK.md`  
   Certified-state ledger and old-to-new terminology crosswalk so current maturity claims stay tied to proof artifacts.

## Current strategic corrections reflected

- CityBrain is not permanently “review-only.” It starts at review/proposal authority but should evolve into governed operations with progressive authority.
- ASK v1.1 is treated as closed/published and moving to app handoff preflight.
- Metropolis/VSS is treated as closed at bounded candidate-observation proof level, not as a citywide perception product.
- Omniverse/WebRTC R5 is treated as closed at functional proof level, not as finished spatial UX.
- CHECK is corrected from “caution mode” to evidence sufficiency / claimability / contradiction / freshness / boundary validation.
- Agents are introduced as the missing active layer: modes are capabilities, agents are workers, the orchestrator governs them.
- No new data source should be onboarded without a consuming intelligence function.

## Recommended next documentation step

After these are reviewed, create a shorter executive deck or one-page product narrative from Docs 01–04. Use Doc 05 for build agents and implementation contracts.


## R2 additions

- Certified-state ledger for ASK v1.1, ASK app handoff, R7/R8/R22 perception, Metropolis/VSS, DeepStream runtime, Omniverse/WebRTC R5, CHECK, Event Fabric, WATCH, BRIEF, RECALL, DIFF, CER/SEG, Workflow, and Production Authority.
- DeepStream runtime readiness recorded for CityBrain R9 local/replay on `txr-4070`.
- ASK v1.1 updated as closed/published with app handoff and fixture vendoring passed; next work is app consumption, not ASK core extension.
- Metropolis/VSS updated as bounded local/replay candidate-review lane; VSS remains narrative review context, not fact source.
- Omniverse/WebRTC R5 updated as closed functional proof; UI/UX and native Kit polish remain later product lane.
- CHECK split into v0/v1.
- Event Fabric split into v0/v1/v2.
- Flows/cartridges preserved as packaging layer over modes.
- Perception privacy/candidate-observation policy added.

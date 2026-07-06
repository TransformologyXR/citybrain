# CityBrain Authoritative Docs R2 Changelog

Date: 2026-07-05

## Why R2 exists

R2 patches the v1 authoritative docs after review showed that the strategy layer needed stronger engineering traceability. It adds proof-ledger discipline, old-to-new terminology mapping, and latest running-track statuses.

## Main changes

1. Added `06_CITYBRAIN_CERTIFIED_STATE_LEDGER_AND_TERMINOLOGY_CROSSWALK.md`.
2. Added certified-state ledger to Doc 01 and Doc 04.
3. Added DeepStream runtime readiness for CityBrain R9 local/replay on `txr-4070`.
4. Updated ASK v1.1 as closed/published, with app handoff and fixture vendoring passed.
5. Updated Metropolis/VSS as closed bounded local/replay candidate-review lane, not production live CCTV.
6. Updated Omniverse/WebRTC R5 as closed functional proof, with UI/UX parked.
7. Split CHECK into v0 and v1 across Docs 02, 04, and 05.
8. Split Event Fabric into v0/v1/v2 across Docs 02, 04, and 05.
9. Added perception privacy and candidate-observation policy to Doc 05.
10. Preserved flows/cartridges as product/scenario packaging over modes.
11. Restated canonical entity ID format.
12. Added a roadmap warning: the roadmap is a dependency map, not a parallel build list.

## Recommended next build order

```text
1. AuthorityEnvelope v1 + common packet fields
2. CHECK v0
3. ASK v1.1 app consumption polish
4. Event Fabric v0
5. Watch Scout v1 with 3–4 query families
6. Perception-to-review app-route integration
7. Omniverse UI/UX later, not now
```

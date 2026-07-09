# MAIN-CITYBRAIN-D8-LONDON-MOBILITY-CORRIDOR-COHERENCE-REVIEW-R1

Goal: check whether the current London mobility source records form a coherent viewer scenario or are only source examples.

Inputs:
- London mobility source-record bundle.
- integrated source-record UI bundle.
- current web UI truth register.

Review questions:
1. Do the London records reference the same corridor or area?
2. Are they tied to a lane blockage, road disruption, route segment, access constraint, or only general mobility infrastructure?
3. Is there a timestamp/currentness field?
4. Is there a real mobility issue record or just static infrastructure records (e.g. EV charging sites)?
5. Can the UI honestly call this a "corridor access issue", or must it be reframed as "source-record gallery plus blockers"?

Produce:
- `LONDON_MOBILITY_CORRIDOR_COHERENCE_REVIEW_R1_DECISION.json`
- `LONDON_SOURCE_RECORD_COHERENCE_MATRIX.json`
- `DEMO_STORY_COHERENCE_VERDICT.md`
- `UI_NARRATIVE_ALLOWED_CLAIMS.json`
- `HASH_MANIFEST.json`

Possible outcomes:
- `PASS_COHERENT_CORRIDOR_SCENARIO`
- `PARTIAL_SOURCE_RECORDS_VALID_BUT_SCENARIO_NOT_COHERENT`
- `FAIL_UI_OVERCLAIMS_SOURCE_LINKAGE`

Do not upgrade static EV/site records into a lane-blockage incident without a source record that proves it.

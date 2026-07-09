# 01 — Execution Model

## Phase 0 is preflight, not the whole task

Codex should first inspect available mobility-related sources and context.

Then:

### If enough mobility context exists

Continue to:

`PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS`

### If mobility context is thin but useful

Continue to:

`PASS_MOBILITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS`

This means the pack is valid as a domain scaffold with DATA_FIRST limitations and sample candidates, but not a rich mobility runtime pack.

### If no meaningful mobility context exists

Stop with:

`WAITING_ON_MOBILITY_INPUT_ROOTS`

## Do not pad

If mobility data is missing, do not fabricate traffic state, road impacts, route disruptions, or certified model outputs.

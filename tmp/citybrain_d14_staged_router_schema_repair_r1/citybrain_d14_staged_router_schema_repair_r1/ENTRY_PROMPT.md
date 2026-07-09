# ENTRY PROMPT — MAIN-CITYBRAIN-D14-STAGED-ROUTER-SCHEMA-REPAIR-R1

Run the D14 staged-router schema repair. Do not continue the flat-route v0.4B line.

## Sequence

1. `MAIN-CITYBRAIN-D14-STAGED-ROUTER-SCHEMA-PREFLIGHT-R1`
2. `MAIN-CITYBRAIN-D14-STAGED-SCHEMA-CONTRACT-R1`
3. `MAIN-CITYBRAIN-D14-FLAT-LABEL-MIGRATION-TO-STAGED-R1`
4. `MAIN-CITYBRAIN-D14-HARD-SHAPED-TOPUP-PROTOCOL-R2`
5. `MAIN-CITYBRAIN-D14-STAGED-DOUBLE-LABEL-SAMPLE-R1`
6. `MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-PACKET-R1`
7. `MAIN-CITYBRAIN-D14-STAGED-ROUTER-SCHEMA-CLOSEOUT-R1`

## Hard stop

Stop after producing the staged blind double-label sample and instructions.

Expected status:

`PAUSED_D14_STAGED_ROUTER_SCHEMA_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Do not run Split/Seal R3.
Do not open router preflight.
Do not train router.
Do not claim real operator validation.

## Prior state to consume

Use the latest available D14 corpus and failed comparison artifacts from:

- `outputs/main_citybrain_d14_route_taxonomy_repair_v04b_boundary_stability_r1/`
- earlier v0.4A/v0.3 artifacts only as needed for audit history.

If required source artifacts are missing, emit a blocked/partial decision with exact missing paths.

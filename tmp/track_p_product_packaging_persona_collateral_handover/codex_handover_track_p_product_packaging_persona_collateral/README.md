# Codex Handover — Track P Product Packaging / Persona / Collateral

This package is for a third parallel Codex thread:

`Track P — Product Packaging / Persona / Collateral`

It is intended to run while Track A and Track D run in separate Codex threads.

## Goal

Package the frozen Hero Neighbourhood Control Room Reference Demo into a clear outward-facing collateral bundle:

- persona rendering policies
- operator walkthrough
- executive walkthrough
- planner/analyst variants
- claim-label audit
- README / repo handoff notes
- capture checklist
- collateral manifest
- closeout package

## Non-goal

Do not build new platform functionality. Do not mutate upstream outputs. Do not wait for Track A or Track D.

## Run order

1. `prompts/P0_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_PROMPT.md`
2. `prompts/P1_PERSONA_RENDERING_POLICIES_R1_PROMPT.md`
3. `prompts/P2_HERO_NEIGHBOURHOOD_COLLATERAL_PACK_R1_PROMPT.md`
4. `prompts/P3_PRODUCT_PACKAGING_CLOSEOUT_PROMPT.md`

## Suggested task names

- `MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-AND-PERSONA-PREFLIGHT`
- `MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1`
- `MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-COLLATERAL-PACK-R1`
- `MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT`

## Success definition

Track P closes when a reviewer can open one local index and understand:

- what the frozen demo is
- what it proves
- what it does not prove
- how each persona sees the same evidence
- how Omniverse and web companion divide responsibility
- what limitations and non-blocking gaps remain
- which files support the walkthrough / README / claim labels

## Boundary

Track P is packaging and narrative. It must not make production, live monitoring, action, dispatch, enforcement, or certified-twin claims.

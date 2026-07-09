# Prompt — MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT

You are Codex working in the CityBrain repository.

Task:

`MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT`

Purpose:

Close Track P — Product Packaging / Persona / Collateral — as a frozen collateral-ready package for the Hero Neighbourhood Control Room Reference Demo.

This is a closeout only. Do not create new product functionality.

Required upstreams:

- `outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight`
- `outputs/main_citybrain_d6_persona_rendering_policies_r1`
- `outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1`
- `outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1`
- `outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review`

Use output root:

`outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout/`

Create:

- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json`
- `README.md`
- `LOCAL_OPEN_INDEX.md`
- `PACKAGING_ACCEPTANCE_MATRIX.json`
- `PERSONA_POLICY_REVIEW.json`
- `COLLATERAL_REVIEW.json`
- `CLAIM_LABEL_REVIEW.json`
- `LIMITATIONS_DISCLOSURE_REVIEW.json`
- `CAPTURE_READINESS_REVIEW.json`
- `REPO_HANDOFF_REVIEW.json`
- `FINAL_TRACK_P_STATUS.md`
- `NEXT_TRACK_OPTIONS.md`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Acceptance matrix must verify:

- P0 preflight is green.
- Persona R1 is green.
- Collateral Pack R1 is green.
- Four personas exist.
- Collateral manifest exists.
- Walkthrough scripts exist.
- Capture checklist exists.
- Claim-label audit exists.
- Limitations ledger includes 21 unresolved/quarantined contexts and 3 non-blocking gaps.
- Repo README draft exists.
- No over-claiming.
- No upstream mutation.

Next track options should say:

- If Track A and Track D are still running, wait for them before Collateral R2.
- If Track A and Track D are green, create a Collateral R2 that includes real twin/action governance enhancements.
- If external demo is needed immediately, use Track P outputs as the R1 outward collateral.

Success status:

`PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS`

Failure status:

`FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT`

Final response should include:

- final status
- output root
- personas count
- collateral artifact count
- claim-label status
- limitations disclosure status
- capture readiness status
- no-action/no-mutation/secret/hash statuses
- recommended next task

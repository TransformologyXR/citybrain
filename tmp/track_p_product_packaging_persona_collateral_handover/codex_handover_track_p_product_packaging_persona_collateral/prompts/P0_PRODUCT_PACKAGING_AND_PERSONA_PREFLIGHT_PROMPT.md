# Prompt — MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-AND-PERSONA-PREFLIGHT

You are Codex working in the CityBrain repository.

Task:

`MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-AND-PERSONA-PREFLIGHT`

Purpose:

Prepare a packaging/persona/collateral lane for the frozen Hero Neighbourhood Control Room Reference Demo. This is a preflight only. It must define the scope and verify upstreams before persona and collateral artifacts are authored.

Context:

Use the shared context in `00_SHARED_CONTEXT.md`.

Important: this lane should not wait for Track A “The Twin, For Real” or Track D “HITL Reviewed Action.” Those are separate enhancement lanes. This lane packages the currently frozen demo.

Required upstreams to discover:

- `outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1`
- `outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1`
- `outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review`
- `outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout`
- `outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout`
- `outputs/main_citybrain_d6_incident_mode_closeout`
- `outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4`

If any required upstream is missing, fail safely and record the missing upstream. Do not fabricate facts.

Preflight outputs:

Use output root:

`outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight/`

Create:

- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_DECISION.json`
- `README.md`
- `LOCAL_OPEN_INDEX.md`
- `UPSTREAM_DISCOVERY.json`
- `FROZEN_DEMO_FACTS.json`
- `TRACK_P_SCOPE_CONTRACT.json`
- `PERSONA_RENDERING_SCOPE.md`
- `COLLATERAL_SCOPE.md`
- `NON_BLOCKING_GAPS_CARRY_FORWARD.md`
- `CLAIM_LABEL_BASELINE.md`
- `VALIDATION_PLAN.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Scope contract must state:

- Track P is packaging and narrative, not new platform functionality.
- Personas are deterministic rendering policies over the same evidence bundle / packets.
- Persona policies must not create separate agents or separate truth paths.
- Collateral must carry forward the three non-blocking gaps and the preserved unresolved/quarantined contexts.
- Final video/collateral capture should wait until Persona R1 is green.
- Track A and Track D outputs, if present, may be mentioned as future/deepening lanes but are not dependencies.

Validation:

- Required upstreams discovered.
- Frozen demo status is green.
- Integration readiness review is green.
- Non-blocking gaps are copied forward.
- No production/public API/citywide certified twin/live monitoring/alert/dispatch/routing/control/enforcement/legal/certified/automated action claim.
- No mutation to upstream artifacts.
- No secrets.
- Hash manifest verifies generated artifacts.

Success status:

`PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT_WITH_LIMITATIONS`

Failure status:

`FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_AND_PERSONA_PREFLIGHT`

Final response should include:

- final status
- output root
- upstream discovery count
- missing upstream count
- frozen demo facts summary
- boundary audit status
- recommended next task: `MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1`

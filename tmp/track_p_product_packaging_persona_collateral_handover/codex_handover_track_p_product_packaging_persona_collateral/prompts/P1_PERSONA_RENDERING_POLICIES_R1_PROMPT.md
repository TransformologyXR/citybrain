# Prompt — MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1

You are Codex working in the CityBrain repository.

Task:

`MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1`

Purpose:

Create deterministic persona rendering policies for the frozen Hero Neighbourhood Control Room Reference Demo.

This task must make the demo read like a product without introducing new truth paths, new agents, or autonomous behavior.

Personas:

- Executive
- Operator
- Planner
- Analyst

Core rule:

All personas render the same underlying evidence, packets, limitations, unresolved/quarantined contexts, and claim boundaries. They differ only in framing, level of detail, and recommended view emphasis.

Required upstream:

- `outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight`
- frozen demo upstreams identified by preflight

Use output root:

`outputs/main_citybrain_d6_persona_rendering_policies_r1/`

Create:

- `MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_DECISION.json`
- `README.md`
- `LOCAL_OPEN_INDEX.md`
- `PERSONA_POLICY_SCHEMA.json`
- `PERSONA_POLICIES.json`
- `PERSONA_POLICIES.md`
- `EXECUTIVE_VIEW_POLICY.md`
- `OPERATOR_VIEW_POLICY.md`
- `PLANNER_VIEW_POLICY.md`
- `ANALYST_VIEW_POLICY.md`
- `SHARED_EVIDENCE_INVARIANTS.md`
- `PERSONA_BOUNDARY_AUDIT.json`
- `PERSONA_DRIFT_AUDIT.json`
- `PERSONA_RENDERING_FIXTURES.json`
- `PERSONA_RENDERING_FIXTURE_RESULTS.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Persona policy requirements:

Executive:

- concise outcome/status summary
- what is proven
- what remains limited
- no operational command language
- shows bounded/local/replay/demo status clearly

Operator:

- packet-oriented view
- affected entities and overlays
- unresolved/quarantined contexts visible
- safe next-look framing only
- no alerts, dispatch, enforcement, or automatic workflow

Planner:

- spatial/contextual implications
- graph/edge context emphasis
- scenario/corridor framing
- no prediction or plan execution claim unless already evidence-backed

Analyst:

- evidence refs, limitation refs, validation status
- compatibility notes
- non-blocking gaps and unresolved contexts
- audit details

Negative tests:

- Persona cannot omit limitations.
- Persona cannot turn unresolved/quarantined context into confirmed truth.
- Persona cannot convert safe-next-look into an action instruction.
- Persona cannot imply live monitoring or alerting.
- Persona cannot claim a certified citywide twin.

Validation:

- Four personas generated.
- All personas reference same evidence/limitation facts.
- Persona rendering fixtures pass.
- Persona drift audit passes.
- No mutation to upstreams.
- Boundary audits pass.
- Hash manifest passes.

Success status:

`PASS_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1_WITH_LIMITATIONS`

Failure status:

`FAIL_MAIN_CITYBRAIN_D6_PERSONA_RENDERING_POLICIES_R1`

Recommended next task:

`MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-COLLATERAL-PACK-R1`

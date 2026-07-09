Task: `MAIN-CITYBRAIN-D6-CROSS-CITY-CROSS-DOMAIN-EXPANSION-SCOUT-PREFLIGHT`

Build a scout preflight that discovers current green CityBrain artifacts relevant to cross-city/cross-domain expansion.

Inputs to inspect:
- latest sprint certified-state/handover refresh
- R2 certified-state/handover refresh
- CER/SEG v2 closeout
- R7/R8 edge registry
- decision-support option-set contract
- cross-domain cascade closeout
- similar-case retrieval closeout
- city/domain cartridges already present in outputs

Outputs:
- `INPUT_ARTIFACT_INDEX.json`
- `SCOUT_SCOPE.md`
- `EXPANSION_SCOUT_PREFLIGHT_DECISION.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`


Boundary invariants:
- local/replay/review/query context only unless a later separately approved gate says otherwise.
- no production/public API claim.
- no autonomous monitoring, alerts, dispatch, routing/control, enforcement, legal/certified finding, official ticket/case creation, or automated action.
- no citywide certified twin or certified physical geometry claim.
- no mutation of frozen upstream outputs.
- use additive outputs under outputs/<task_name>/ and scripts/run_<task_name>.py only.
- include claim-boundary, no-action, no-mutation, secret, validation, hash manifest, and local open index artifacts.

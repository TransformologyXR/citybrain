# MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-CLOSEOUT

Objective: close the similar-case retrieval lane and define how its outputs integrate with Plan Mode and later inverse dynamics.

Required upstreams:
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-INDEX-R1`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-QUALITY-GATE-R3`

Output root:
`outputs/main_citybrain_d6_similar_case_retrieval_closeout/`

Runner:
`scripts/run_main_citybrain_d6_similar_case_retrieval_closeout.py`

Produce:
- `MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `SIMILAR_CASE_ACCEPTANCE_MATRIX.json`
- `INDEX_REVIEW.json`
- `OPTION_SET_ATTACHMENT_REVIEW.json`
- `QUALITY_GATE_REVIEW.json`
- `PLAN_MODE_INTEGRATION_NOTES.json`
- `INVERSE_DYNAMICS_INTEGRATION_NOTES.json`
- `LIMITATIONS_LEDGER.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- all upstream retrieval tasks green or fail-safe
- at least one option-set attachment fixture produced if relevant cases exist
- no overclaim or action claim
- quality gate discriminates good from broken cases
- integration notes explain how Track B and future inverse dynamics consume `similar_case_refs[]`

Success status:
`PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

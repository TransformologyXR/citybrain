# MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT

Objective: preflight a local/replay similar-case retrieval lane that can attach cross-city precedent/context to Track S `reviewed_option_set` objects.

This lane does not require SUMO and can run in parallel with Plan Mode/SUMO after Track S is green.

Required upstreams:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH`
- `MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT`
- `MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING`

Supporting upstreams:
- NYC/London/Chicago/Barcelona accepted snapshots where available
- Incident Mode closeout
- Hero USD Twin HITL final package review

Output root:
`outputs/main_citybrain_d6_similar_case_retrieval_preflight/`

Runner:
`scripts/run_main_citybrain_d6_similar_case_retrieval_preflight.py`

Produce:
- `MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_PREFLIGHT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `CASE_SOURCE_INVENTORY.json`
- `CASE_FEATURE_MODEL_SPEC.json`
- `SIMILAR_CASE_REF_CONTRACT.json`
- `OPTION_SET_ATTACHMENT_PLAN.json`
- `RETRIEVAL_LIMITATIONS.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- required upstreams found and green
- retrieval source inventory produced
- deterministic feature model defined
- no vector DB, cuVS, NeMo Retriever, or LLM dependency required for pass; record as future optional if absent
- similar cases are precedent/context only, not proof of same outcome
- reviewed_option_set schema attachment plan present

Success status:
`PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_PREFLIGHT_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_PREFLIGHT`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

# MAIN-CITYBRAIN-D6-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2

Objective: retrieve similar cases for the shared hero corridor scenario and attach `similar_case_refs[]` to reviewed option-set fixtures.

Required upstreams:
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-INDEX-R1`
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

Output root:
`outputs/main_citybrain_d6_similar_case_option_set_attachment_r2/`

Runner:
`scripts/run_main_citybrain_d6_similar_case_option_set_attachment_r2.py`

Produce:
- `MAIN_CITYBRAIN_D6_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `SIMILAR_CASE_QUERY_FIXTURES.json`
- `SIMILAR_CASE_QUERY_RESULTS.json`
- `REVIEWED_OPTION_SETS_WITH_SIMILAR_CASES.json`
- `REVIEWED_OPTION_SETS_WITH_SIMILAR_CASES.jsonl`
- `ATTACHMENT_SCHEMA_VALIDATION_REPORT.json`
- `CASE_RELEVANCE_EXPLANATION_REPORT.json`
- `CASE_LIMITATION_CARRY_FORWARD.json`
- `TRACK_D_PROMOTION_BOUNDARY_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- similar_case_refs attach to option sets without changing execution state
- no Track D proposal promotion
- similar cases include provenance and limitations
- do-nothing baseline and abstain/no-safe-option semantics preserved
- attachment validates against Track S reviewed_option_set schema

Success status:
`PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

# MAIN-CITYBRAIN-D6-SIMILAR-CASE-INDEX-R1

Objective: build a deterministic local similar-case index from accepted cross-city / cross-domain artifacts.

Required upstream:
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT`

Output root:
`outputs/main_citybrain_d6_similar_case_index_r1/`

Runner:
`scripts/run_main_citybrain_d6_similar_case_index_r1.py`

Produce:
- `MAIN_CITYBRAIN_D6_SIMILAR_CASE_INDEX_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `SIMILAR_CASE_INDEX_SCHEMA.json`
- `SIMILAR_CASE_INDEX.json`
- `SIMILAR_CASE_INDEX.jsonl`
- `CASE_FEATURE_ROWS.jsonl`
- `CASE_PROVENANCE_REPORT.json`
- `CASE_CITY_DOMAIN_COVERAGE_MATRIX.json`
- `INDEX_BUILD_LIMITATIONS.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Minimum index fields:
- `case_id`
- `source_city`
- `source_flow_or_track`
- `scenario_family`
- `event_family`
- `affected_entity_types`
- `relationship_families`
- `option_or_response_context_refs`
- `outcome_summary`
- `evidence_refs`
- `limitation_refs`
- `review_state`
- `provenance`

Acceptance:
- index built from accepted local artifacts only
- no mutation of source outputs
- provenance and limitations preserved
- city/domain coverage matrix produced
- no claim that similar cases determine current outcome

Success status:
`PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_INDEX_R1_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_SIMILAR_CASE_INDEX_R1`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

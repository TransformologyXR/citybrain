# MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-QUALITY-GATE-R3

Objective: create and run a discriminating quality gate for similar-case retrieval.

This gate must test more than parse/schema. It must catch wrong-city, wrong-domain, stale, overclaimed, and unsupported retrieval behavior.

Required upstream:
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2`

Output root:
`outputs/main_citybrain_d6_similar_case_retrieval_quality_gate_r3/`

Runner:
`scripts/run_main_citybrain_d6_similar_case_retrieval_quality_gate_r3.py`

Produce:
- `MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_QUALITY_GATE_R3_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `GOLDEN_RETRIEVAL_CASES.json`
- `GOLDEN_RETRIEVAL_RESULTS.json`
- `QUALITY_GATE_REPORT.json`
- `NEGATIVE_RETRIEVAL_TESTS.json`
- `OVERCLAIM_DETECTION_REPORT.json`
- `CITY_DOMAIN_DIVERSITY_REPORT.json`
- `STALE_OR_LIMITED_CASE_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Minimum tests:
- retrieves at least one plausible similar case when available
- flags no-good-match when no relevant case exists
- rejects wrong-domain high-overlap lexical match
- rejects wrong-city overclaim when provenance is incompatible
- carries source limitations into option-set attachment
- does not present similar case as proof of outcome
- preserves `execution_state = not_executed`

Success status:
`PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_QUALITY_GATE_R3_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_QUALITY_GATE_R3`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

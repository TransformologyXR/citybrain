# ASK v1.1 Real Corpus Eval R1 Summary

## Final decision

`PASS_ASK_V11_REAL_CORPUS_EVAL_R1_WITH_LIMITATIONS`

## Scope

Eval-only retained local corpus harness. No G1-G8 runtime behavior is changed or called.

## Results

- Cases: 18/18 evaluated cases passed
- Total matrix cases: 19
- Ready cases: 10
- Needs-mapping cases: 8
- Excluded cases: 1
- Sev-4 real failures: 0
- Boundary/action Sev-4 count: 0
- Raw-query leak count: 0
- Official action claim count: 0
- Future-flow runtime violation count: 0
- Source URL citations counted but not fetched: 114

## Severity summary

- sev_0_clean: 10
- sev_1_taxonomy_reporting_only: 9
- sev_2_acceptable_but_weak: 0
- sev_3_audit_uncertain: 0
- sev_4_real_failure: 0

## Family summary

- board_meta: 1
- boundary_action: 1
- boundary_identity_person: 1
- boundary_prediction: 1
- candidate_inferred_link: 1
- contradiction: 1
- entity_profile: 1
- external_context_need: 1
- no_data: 1
- patch_queue_query: 1
- proximity_vs_causality: 1
- raw_query_boundary: 1
- renderer_no_undowngrade: 1
- selected_item_followup: 1
- source_record_profile: 1
- staleness: 1
- subject_answer: 1
- unanchored_city_ask: 1
- unsupported_template_gap: 1

## Contract boundaries

- Retained local corpus only.
- No live retrieval.
- No production API.
- No official action, ticket, dispatch, enforcement, or autonomous workflow.
- No legal or certified determination.
- WATCH/BRIEF/DIFF/INCIDENT remain skeleton-only.

## Limitations

- R1 is an eval-only harness over retained local corpus artifacts.
- G1-G8 runtime, packet schemas, registries, CHECK, and renderer behavior are unchanged.
- Needs-mapping cases are mapped by the eval adapter only, not by runtime G5.
- The contradiction family remains excluded until a retained conflicting-value pair is available.
- URLs embedded in retained artifacts are counted as citations only and are never fetched.

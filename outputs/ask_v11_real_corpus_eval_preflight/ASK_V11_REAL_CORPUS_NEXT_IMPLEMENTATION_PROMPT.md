# ASK-V11-REAL-CORPUS-EVAL-R1

STATUS: IMPLEMENT EVAL HARNESS ONLY - DO NOT CHANGE ASK RUNTIME

CONTEXT:
ASK v1.1 is sealed and published. The real-corpus preflight found retained local CityBrain corpus artifacts that can be evaluated against ASK v1.1 families, but current G5 runtime remains intentionally fixture-only.

GOAL:
Implement a real retained corpus eval harness for ASK v1.1 without changing G1-G8 runtime behavior.

DO NOT:
- change G1-G8 runtime
- change packet schemas
- change concept registry seed
- change template registry
- change CHECK rules
- change renderer rules
- implement WATCH/BRIEF/DIFF/INCIDENT runtime
- add live retrieval
- add production API
- add official action/ticket/dispatch/enforcement behavior
- call external services
- rerun or rewrite sealed eval artifacts unless explicitly requested

ALLOWED:
- add eval-only corpus case definitions
- add eval-only corpus readers/adapters for retained local artifacts
- read retained local corpus JSON/Markdown only
- map retained source records into eval evidence observations
- add tests for the eval harness
- report Sev-4 failures separately

INPUT ARTIFACTS:
- outputs/ask_v11_real_corpus_eval_preflight/ASK_V11_REAL_CORPUS_CASE_MATRIX.json
- packages/fixtures/brain_surface_story_queue/primary_story_queue.json
- packages/fixtures/brain_surface_story_queue/brain_surface_story_queue_bundle.json
- packages/fixtures/story_first_demo/story_source_bundle.json
- packages/fixtures/london_mobility_source_records/source_record_bundle.json
- packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json
- packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json
- packages/fixtures/source_record_ui_integrated/source_record_gap_closure_records.json
- packages/fixtures/mobility_access/runtime_bundle/evidence_bundle.json
- packages/fixtures/mobility_access/runtime_bundle/review_state.json
- packages/fixtures/mobility_access/runtime_bundle/limitations.json
- packages/fixtures/d9_product_modes/runtime_bundle/D9_PRODUCT_MODE_RUNTIME_BUNDLE.json

REQUIRED R1 BEHAVIOR:
1. Load the preflight case matrix.
2. Load retained local corpus artifacts only.
3. Evaluate ready cases and needs-mapping cases using an eval-only adapter.
4. Preserve the canonical ASK v1.1 runtime unchanged.
5. Mark excluded cases explicitly.
6. Report:
   - total cases
   - pass/fail counts
   - Sev-4 count
   - boundary action Sev-4 count
   - raw_query leak count
   - official action claim count
   - future-flow runtime violation count
   - no-data/cannot-claim coverage
7. Fail hard on:
   - live retrieval attempt
   - production API call
   - official action/ticket/dispatch claim
   - legal/certified conclusion claim
   - G3 invented retrieval plan
   - renderer un-downgrade
   - raw_query leakage
   - future-flow runtime behavior

IMPORTANT:
Any runtime fix must be a later package after R1 exposes a concrete failure. R1 may report a runtime gap, but it must not repair it.

EXPECTED OUTPUTS:
- outputs/ask_v11_real_corpus_eval_r1/ASK_V11_REAL_CORPUS_EVAL_R1_REPORT.json
- outputs/ask_v11_real_corpus_eval_r1/ASK_V11_REAL_CORPUS_EVAL_R1_SUMMARY.md
- outputs/ask_v11_real_corpus_eval_r1/ASK_V11_REAL_CORPUS_EVAL_R1_FAILURES.md
- tests for eval harness only

NEXT PACKAGE:
ASK-V11-REAL-CORPUS-EVAL-R1

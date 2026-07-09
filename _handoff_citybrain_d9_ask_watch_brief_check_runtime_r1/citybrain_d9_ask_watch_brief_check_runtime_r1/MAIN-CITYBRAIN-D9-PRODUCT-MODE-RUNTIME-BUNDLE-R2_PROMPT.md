# MAIN-CITYBRAIN-D9-PRODUCT-MODE-RUNTIME-BUNDLE-R2

Build the local product-mode runtime bundle from certified/recovered inputs.

## Bundle contents

- story_queue_index
- source_record_index
- ask_question_library
- watch_named_query_registry
- brief_templates
- check_rules
- recall_cutaway_examples
- deferred_diff_and_perception_ledger
- one_truth_product_mode_index

## Required source coverage

Minimum:
- London Wood Lane Ask/Brief source context
- NYC MVC cascade Ask/Brief source context
- Watch query registry with at least:
  - `watch:proximity_works_to_access@v1`
  - `watch:incident_to_candidate_asset_context@v1`
  - `watch:low_confidence_link_or_source_gap@v1`
- Check rule set with claim/source-depth/no-action checks
- Recall cutaway with Chicago match-reason gating or documented partial

## Required artifacts

- `packages/fixtures/d9_product_modes/runtime_bundle/D9_PRODUCT_MODE_RUNTIME_BUNDLE.json`
- `D9_PRODUCT_MODE_ONE_TRUTH_INDEX.json`
- `D9_RUNTIME_BUNDLE_SOURCE_MAP.json`
- `D9_RUNTIME_BUNDLE_GAP_LEDGER.json`
- `D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_WITH_LIMITATIONS`

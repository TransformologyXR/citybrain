# Eval Representativeness Audit R1

Final status: `PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS`

## Answer

- Eval corpus: 48 cases across 4 families and 12 case types.
- Founder probe: 16 cards across 4 families and 4 scenarios.
- Synthetic factory: 66737 main acquisition rows, 144 seed entities, 55 replay events, 11 each for WATCH/ASK/CHECK/BRIEF/SPATIAL, and 6 runtime/control-room cards.

The current 48-case eval corpus is representative enough for bounded internal regression and founder diagnostic review. It is not representative enough for founder product-readiness review, client readiness, or learning readiness.

## Weakest Axes

- `source_class_coverage`: thin - Eval rows are dominated by replay source_class; official/native/sensor/model-generated classes are not represented as independent classes.
- `event_lifecycle_coverage`: partial - Quarantine and local replay handling appear, but late/superseded/expired/duplicate lifecycle states are not explicit enough.
- `simulation_option_engine_coverage`: thin - Current 48 eval cases mostly mark simulation as not applicable; separate option-engine artifacts exist but are not deeply represented in the founder cards.
- `native_vs_derived_backfill_coverage`: partial - Founder cards expose derived overlay refs for mobility cards, but native-vs-derived provenance is not consistently visible across all cards.
- `city_domain_source_variety`: partial - The selected product-loop families span building, city asset, mobility, and permit domains, but the new synthetic Dubai factory layers are only partially reflected.
- `synthetic_data_factory_coverage`: partial - Product fixtures, event replay, runtime, and control-room layers are now available, but the current eval/founder corpus was not built to sample all 66,737 acquisition rows or 144 seed entities directly.
- `human_review_readiness`: partial - 16 cards are enough for founder diagnostic review, but not product-review or client-readiness review without stronger card evidence summaries and actual review sessions.
- `learning_fuel_readiness`: none - No training rows, labels, dispositions, learned ranking, or model training are created or allowed by this audit.
- `client_demo_readiness`: thin - The material supports an internal bounded demo surface, but no client-ready or production claim should be made.

## Founder Cards

- Diagnostic-ready cards: 16
- Product-review-ready cards: 0
- Main card gap: evidence summaries, CER/SEG context, CHECK actual outcomes, and native-vs-derived provenance need to be embedded rather than referenced.

## Recommendation

- Eval: `EXPAND_CORPUS_BEFORE_CLIENT_OR_LEARNING_READINESS`
- Founder: `PROCEED_TO_FOUNDER_DIAGNOSTIC_REVIEW_NOT_PRODUCT_READINESS_REVIEW`

## Boundaries

This audit is read-only. It creates no founder session result, operator fuel, training row, forecast surface, live ingestion claim, source-truth mutation, official case/workflow, dispatch/control/enforcement action, legal/certified finding, or client-ready claim.

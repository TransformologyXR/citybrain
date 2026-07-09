# Codex Prompt — CityBrain Eval Representativeness Audit R1

## Package

`MAIN-CITYBRAIN-EPOCH4-EVAL-REPRESENTATIVENESS-AUDIT-R1`

## Mission

Audit representativeness of the current CityBrain Epoch 4 evaluation and founder-probe material.

Do **not** add new product behavior. Do **not** mutate source truth. Do **not** run a founder session. Do **not** create operator fuel. Do **not** create training rows. Do **not** create product forecast surfaces.

This package answers:

1. What do the 48 eval cases cover?
2. What do the 16 founder-probe cards cover?
3. What product/data/failure-mode axes are missing?
4. Which current founder cards are product-review-ready vs diagnostic-only vs not-ready?
5. How should the eval corpus be expanded next, if at all?
6. How does the synthetic Dubai data-factory work change the coverage picture?

## Context to preserve

The current 16 founder cards are **4 families × 4 scenarios**:

- `building_compliance_perception_candidate`
- `city_asset_infrastructure_issue`
- `mobility_access_interruption_v0`
- `permit_inspection_delay`

Scenarios:

- `positive_packet_baseline`
- `negative_no_data`
- `stale_freshness`
- `contradiction_pair`

The 16 cards are a human-probe sample, not a global product audit.

The 48 eval cases are an engineering/regression corpus, not a client-readiness or learning-readiness corpus.

An uploaded external thread summary says the synthetic data factory now contains, among other items:

- `66,737` main acquisition fuel rows.
- `144` synthetic seed entities.
- `55` replay events.
- `11` fixtures each for WATCH, ASK, CHECK, BRIEF, and SPATIAL.
- `6` localhost runtime packets/responses and `6` control-room cards.

Treat that as **source/context material**. Do not treat it as official Dubai truth.

## Inputs to discover

Use best-effort discovery. Do not fail merely because a root has a slightly different name; record missing roots in `MISSING_INPUTS.json`.

Look for:

```text
outputs/main_citybrain_epoch4_eval_corpus_expansion_r2
outputs/main_citybrain_epoch4_product_loop_eval_corpus_r1
outputs/main_citybrain_epoch4_product_loop_challenge_negative_suite_r1
outputs/main_citybrain_epoch4_candidate_fix_effect_sandbox_r1
outputs/main_citybrain_epoch4_derived_fix_promotion_overlay_r1
outputs/main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1
outputs/main_citybrain_epoch4_founder_probe_review_pack_assembler_r1
outputs/main_citybrain_epoch4_review_packet_360_r1
outputs/main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1
outputs/main_citybrain_epoch4_product_readiness_gap_closure_sequence_r1
outputs/main_citybrain_epoch4_after_deepening_cross_track_reverify_r1
outputs/main_citybrain_epoch4_data_maturity_diagnostic_product_r2
outputs/main_citybrain_track4_source_registry_v1
outputs/main_citybrain_epoch4_tracka_event_stories_source_diff_r1
outputs/main_citybrain_epoch4_trackb_maturity_brief_governance_r1
outputs/main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1
outputs/main_citybrain_epoch4_cer_check_event_stress_eval_r1
```

Also consume:

```text
source_refs/SYNTHETIC_DUBAI_DATA_FACTORY_THREAD_SUMMARY.md
```

If you run from the repo and the source ref is missing, use the packaged `source_refs/` file from this handover.

## Required outputs

Write to:

```text
outputs/main_citybrain_epoch4_eval_representativeness_audit_r1/
```

Required files:

```text
REPRESENTATIVENESS_AUDIT_DECISION.json
MISSING_INPUTS.json
EVAL_CORPUS_INVENTORY.json
FOUNDER_CARD_INVENTORY.json
COVERAGE_AXIS_SCORECARD.json
FAMILY_SCENARIO_COVERAGE_MATRIX.json
SOURCE_CLASS_COVERAGE_MATRIX.json
CHECK_REASON_COVERAGE_MATRIX.json
EVENT_LIFECYCLE_COVERAGE_MATRIX.json
EVIDENCE_DEPTH_COVERAGE_MATRIX.json
SIMULATION_COVERAGE_MATRIX.json
CITY_DOMAIN_COVERAGE_MATRIX.json
SYNTHETIC_DATA_FACTORY_CROSSWALK.json
FOUNDER_CARD_READINESS_CLASSIFICATION.json
REPRESENTATIVENESS_FINDINGS.md
EVAL_EXPANSION_RECOMMENDATION_R1.json
FOUNDER_PROBE_RECOMMENDATION_R1.json
NO_OVERCLAIM_GUARD.json
HASH_MANIFEST.json
```

Publication copy:

```text
publications/epoch4/main-citybrain-epoch4-eval-representativeness-audit-r1/
```

## Coverage axes

Score each axis using:

```text
none
thin
partial
adequate_for_internal_regression
strong_internal
not_applicable
```

Audit these axes at minimum:

1. Family coverage.
2. Scenario type coverage.
3. Source class coverage.
4. Event lifecycle coverage.
5. CHECK reason coverage.
6. Evidence depth coverage.
7. Simulation / option-engine coverage.
8. Native vs derived/backfill evidence coverage.
9. City/domain/source variety.
10. Synthetic-data-factory coverage.
11. Human-review readiness.
12. Learning/fuel readiness.
13. Client/demo readiness.

## Classification rules

### Founder card readiness

Each founder card must be classified as one of:

```text
product_review_ready
diagnostic_review_ready
card_repair_needed
product_repair_needed
parked
```

Do not classify a card as `product_review_ready` if it lacks:

- readable evidence summary,
- CER/SEG context,
- CHECK actual outcome,
- cannot-claim / downgrade boundary,
- BRIEF or Review Packet context,
- clear task question for reviewer.

### Eval corpus readiness

Classify the 48 eval corpus as:

```text
bounded_internal_regression_ready
founder_diagnostic_ready
founder_product_review_ready
client_readiness_ready
learning_readiness_ready
```

These are independent booleans with reasons. It is acceptable and likely that only the first two are true.

### Synthetic data factory crosswalk

Map the uploaded synthetic-data summary into product-loop coverage:

```text
base data foundation
mobility donor depth
synthetic seed entities
event replay rows
WATCH/ASK/CHECK/BRIEF/SPATIAL fixtures
runtime packets
control-room cards
```

Then report whether the current 48 eval cases and 16 founder cards actually consume or represent those layers.

## Non-goals / forbidden capabilities

Do not create:

```text
founder session results
operator fuel
training rows
learned ranking
model training
ForecastPacket
product forecast surface
live ingestion claim
official case/ticket/workflow
dispatch/control/enforcement action
source-truth mutation
canonical truth mutation
maturity score inflation
client-ready claim
```

## Acceptance criteria

Pass if:

1. All required JSON/MD outputs exist and parse.
2. The audit explicitly distinguishes regression readiness, founder diagnostic readiness, product review readiness, client readiness, and learning readiness.
3. The audit maps 16 founder cards back to the current eval corpus.
4. The audit maps current eval/founder material to the synthetic data factory summary.
5. The audit produces a prioritized expansion plan.
6. The final decision stays `WITH_LIMITATIONS` unless there is overwhelming evidence otherwise.
7. No forbidden capability is created.

Expected final status:

```text
PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS
```

## Recommended implementation notes

- Build a small Python runner under `scripts/`.
- Add focused tests under `tests/`.
- Prefer JSON-first outputs with Markdown summaries.
- Do not hardcode all paths; use glob discovery where possible.
- Preserve every missing input as an audit fact, not a silent failure.

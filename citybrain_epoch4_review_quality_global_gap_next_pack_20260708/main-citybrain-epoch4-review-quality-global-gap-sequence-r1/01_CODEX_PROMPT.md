# Codex Prompt — MAIN-CITYBRAIN-EPOCH4-REVIEW-QUALITY-GLOBAL-GAP-SEQUENCE-R1

## Mission

Run the next sequence after the deep data estate audit:

```text
1. MAIN-CITYBRAIN-EPOCH4-REVIEW-PACK-QUALITY-UPGRADE-R4-R1
2. MAIN-CITYBRAIN-EPOCH4-DATA-ESTATE-GAP-ROUTING-R1
3. MAIN-CITYBRAIN-EPOCH4-REVIEW-QUALITY-GLOBAL-GAP-FINAL-REVERIFY-R1
```

This sequence exists because the deep audit selected `FIX_REVIEW_PACK_QUALITY_FIRST`, but also exposed global source/freshness/schema/geometry/consuming-flow gaps that must not be ignored.

## Required behavior

- Run sequentially in one worktree.
- Do not run founder session.
- Do not create fuel/training rows.
- Do not mutate source truth.
- Do not claim product readiness unless gates support it.
- Append progress.md entry if AGENTS.md requires it.

## Required outputs

```text
scripts/run_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py
tests/test_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py
outputs/main_citybrain_epoch4_review_quality_global_gap_sequence_r1/REVIEW_QUALITY_GLOBAL_GAP_SEQUENCE_DECISION.json
```

The sequence decision must include:

```text
review_pack_quality_status
data_estate_gap_routing_status
final_reverify_status
founder_session_results_created
operator_fuel_created
training_rows_created
source_truth_mutation
product_review_ready_recommended
founder_diagnostic_ready_recommended
next_recommended_move
```


## Hard boundaries

This package is read-only / additive unless explicitly writing new derived candidate artifacts under `outputs/` and `publications/`.

Do not create or claim:
- founder session results unless a real response input file is supplied for a later package; this package must not run a session.
- operator fuel, training rows, learned arming, learned ranking, model training, or calibration fuel.
- live ingestion, production monitoring, public API, alerting, dispatch, control, enforcement, official case/ticket, legal/certified finding, or source-truth mutation.
- product forecast surface, ForecastPacket, prediction authority, or calibrated simulator claim.
- mutation of raw/provider/source-truth payloads or canonical truth tables.

All fixes must be either:
- review-pack presentation/evidence assembly fixes, or
- derived/candidate overlays, queues, diagnostics, or recommendations.


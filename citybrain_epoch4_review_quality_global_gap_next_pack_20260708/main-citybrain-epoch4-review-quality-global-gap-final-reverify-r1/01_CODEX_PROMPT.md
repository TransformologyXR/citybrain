# Codex Prompt — MAIN-CITYBRAIN-EPOCH4-REVIEW-QUALITY-GLOBAL-GAP-FINAL-REVERIFY-R1

## Mission

Verify that Review Pack Quality Upgrade R4/R5 and Data Estate Gap Routing R1 both completed without overclaiming, source mutation, or fabricated founder/session/fuel artifacts.

## Required inputs

```text
outputs/main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1/
outputs/main_citybrain_epoch4_data_estate_gap_routing_r1/
outputs/main_citybrain_epoch4_deep_data_estate_audit_r1/
outputs/main_citybrain_epoch4_eval_representativeness_audit_r1/
```

## Required outputs

```text
outputs/main_citybrain_epoch4_review_quality_global_gap_final_reverify_r1/
publications/epoch4/main-citybrain-epoch4-review-quality-global-gap-final-reverify-r1/
```

Required artifacts:

```text
REVIEW_QUALITY_GLOBAL_GAP_FINAL_DECISION.json
CARD_READINESS_SUMMARY.json
GLOBAL_DATA_GAP_ROUTING_SUMMARY.json
NEXT_RECOMMENDED_MOVE.json
NO_SESSION_NO_FUEL_REVERIFY.json
NO_SOURCE_TRUTH_MUTATION_REVERIFY.json
NO_FORBIDDEN_CAPABILITY_GUARD.json
HASH_MANIFEST.json
```

## Decision rules

Final status must be one of:

```text
PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_FINAL_REVERIFY_R1_WITH_LIMITATIONS
PARTIAL_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_FINAL_REVERIFY_R1_WITH_LIMITATIONS
FAIL_MAIN_CITYBRAIN_EPOCH4_REVIEW_QUALITY_GLOBAL_GAP_FINAL_REVERIFY_R1
```

The `NEXT_RECOMMENDED_MOVE.json` must choose one:

```text
RUN_FOUNDER_DIAGNOSTIC_REVIEW
REPAIR_REVIEW_PACK_AGAIN
EXPAND_EVAL_CORPUS
DEEPEN_DATA_MATURITY_REMEDIATION
PREPARE_PRODUCT_REVIEW_LATER
```

Do not recommend product-readiness founder review unless the card-readiness gate supports it.


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


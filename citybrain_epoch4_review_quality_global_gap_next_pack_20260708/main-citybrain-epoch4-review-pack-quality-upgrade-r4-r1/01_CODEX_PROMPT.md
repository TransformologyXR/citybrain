# Codex Prompt — MAIN-CITYBRAIN-EPOCH4-REVIEW-PACK-QUALITY-UPGRADE-R4-R1

## Mission

Upgrade the founder/eval review pack after the representativeness audit and deep data estate audit.

Do **not** simply patch the 16 founder cards locally. First classify whether the weakness is:

- card-quality gap,
- product-loop behavior gap,
- native evidence gap,
- derived/backfill provenance gap,
- global source/data gap,
- or intentionally diagnostic negative/stale/contradiction behavior.

Then generate a repaired R4/R5 review pack that is explicitly labeled as one of:

```text
founder_diagnostic_ready
founder_product_review_ready
not_ready
parked
```

## Required inputs

Fail with a clear `MISSING_REQUIRED_INPUTS_WITH_LIMITATIONS` decision if any required input is absent.

Required roots/files:

```text
outputs/main_citybrain_epoch4_eval_representativeness_audit_r1/
outputs/main_citybrain_epoch4_deep_data_estate_audit_r1/
outputs/main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1/
outputs/main_citybrain_epoch4_product_loop_eval_corpus_r1/
outputs/main_citybrain_epoch4_eval_corpus_expansion_r2/
outputs/main_citybrain_epoch4_review_packet_360_r1/ or outputs/main_citybrain_epoch4_review_packet_360_r1-equivalent if superseded
```

Use publication copies only as fallback evidence; source output roots are preferred.

## Required outputs

Write to:

```text
outputs/main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1/
publications/epoch4/main-citybrain-epoch4-review-pack-quality-upgrade-r4-r1/
```

Required artifacts:

```text
REVIEW_PACK_QUALITY_DECISION.json
REVIEW_PACK_QUALITY_BASELINE.json
CARD_TO_EVAL_CASE_COVERAGE_CROSSWALK.json
FOUNDER_CARD_R4_REPAIR_CLASSIFICATION.json
REVIEW_CARD_EVIDENCE_QUALITY_SCORECARD.json
EVAL_CASE_EVIDENCE_ATLAS_48.json
EVAL_CASE_EVIDENCE_ATLAS_48.md
FOUNDER_PROBE_REVIEW_INDEX_R4.md
FOUNDER_PROBE_REVIEW_INDEX_R4.html
FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED_R4.csv
review_cards_r4/*.md
review_cards_r4/*.json
PRODUCT_REVIEW_READINESS_GATE.json
DIAGNOSTIC_REVIEW_READINESS_GATE.json
CARD_GAP_TO_GLOBAL_DATA_GAP_CROSSWALK.json
MOBILITY_NATIVE_VS_DERIVED_PROVENANCE_REPORT.json
NO_SESSION_NO_FUEL_GUARD.json
NO_FORBIDDEN_CAPABILITY_GUARD.json
HASH_MANIFEST.json
```

## Card quality rules

Each card must include:

1. Plain-language case summary.
2. Family and scenario type.
3. Native vs derived/backfill provenance.
4. Source/evidence summary with source class labels.
5. CER/SEG context summary.
6. CHECK v1 actual outcome and expected outcome.
7. Actual-vs-expected pass/fail/explain block.
8. Event state / replay context where applicable.
9. Simulation / option context where applicable, including `not_applicable` when true.
10. BRIEF summary.
11. Spatial context where applicable.
12. Cannot-claim / downgrade reason block.
13. What the founder should judge.
14. Review-readiness classification.

## Decision rules

A card can be `founder_product_review_ready` only if:

- it has actual outcome evidence, not just expected behavior;
- it has CER/SEG context or explicitly says why not applicable;
- CHECK actual outcome is present;
- native/derived provenance is explicit;
- negative/no-data/stale/contradiction cases clearly show safe downgrade behavior;
- if primary evidence is derived/backfill-only, it must be diagnostic unless a native path is also available.

A card can be `founder_diagnostic_ready` if it is useful for diagnosing gaps but not product readiness.

R4 package final decision must be one of:

```text
GO_FOR_FOUNDER_PRODUCT_REVIEW_WITH_LIMITATIONS
GO_FOR_FOUNDER_DIAGNOSTIC_REVIEW_WITH_LIMITATIONS
NO_GO_REPAIR_REQUIRED_WITH_LIMITATIONS
```

Do not claim product readiness unless the gate supports it.

## Tests

Create:

```text
scripts/run_main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1.py
tests/test_main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1.py
```

Tests must verify:

- 16 founder cards accounted for.
- 48 eval cases crosswalked.
- all R4 cards have actual outcome blocks.
- all R4 cards have provenance labels.
- negative/stale/contradiction cards are not incorrectly interpreted as failed product behavior merely because `supports_claim=no`.
- mobility derived backfill is visible and not treated as source truth.
- no session/fuel/training/live/forecast/action/source-truth mutation.


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


# Codex Prompt — MAIN-CITYBRAIN-EPOCH4-DATA-ESTATE-GAP-ROUTING-R1

## Mission

Consume the deep data estate audit and convert its findings into global, candidate-only remediation queues.

Do not fix source truth. Do not inflate maturity scores. Do not silently patch review cards. The goal is to make global data gaps visible, prioritized, and actionable.

## Required inputs

```text
outputs/main_citybrain_epoch4_deep_data_estate_audit_r1/
outputs/main_citybrain_track4_source_registry_v1/ or outputs/main_citybrain_epoch4_track4_source_registry_v1 equivalent
outputs/main_citybrain_epoch4_track5_data_quality_maturity_dashboard_r1/ or latest Data Maturity R2 equivalent
outputs/main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1/ if already run; otherwise continue with a pending reference.
```

## Required outputs

Write to:

```text
outputs/main_citybrain_epoch4_data_estate_gap_routing_r1/
publications/epoch4/main-citybrain-epoch4-data-estate-gap-routing-r1/
```

Required artifacts:

```text
DATA_ESTATE_GAP_ROUTING_DECISION.json
DATA_GAP_ROUTING_LEDGER.json
SOURCE_CLASS_UNKNOWN_TRIAGE_QUEUE.json
FRESHNESS_UNKNOWN_TRIAGE_QUEUE.json
SCHEMA_UNKNOWN_TRIAGE_QUEUE.json
GEOMETRY_UNKNOWN_TRIAGE_QUEUE.json
NO_CONSUMING_FLOW_TRIAGE_QUEUE.json
REVIEW_CARD_GAP_TO_SOURCE_GAP_CROSSWALK.json
SAFE_CANDIDATE_ENRICHMENT_OVERLAYS.json
GLOBAL_GAPS_NOT_FIXED_BY_CARD_REPAIR.md
LOW_HANGING_WINS_ACTION_PLAN.json
DATA_MATURITY_SCORE_NO_INFLATION_GUARD.json
NO_SOURCE_TRUTH_MUTATION_GUARD.json
NO_FORBIDDEN_CAPABILITY_GUARD.json
HASH_MANIFEST.json
```

## Required queue coverage

The deep audit reported at least these counts. Verify from actual deep audit artifacts rather than hardcoding; if counts differ, explain why.

```text
273 sources with no consuming flow
462 unknown freshness
430 unknown source class
456 unknown schema
526 missing/unknown geometry
```

Each queue item should include:

```text
queue_item_id
source_id or artifact_ref
city
domain
current_gap_type
source_class_if_known
freshness_if_known
geometry_status_if_known
schema_status_if_known
candidate_action
safe_to_auto_enrich_boolean
requires_manual_review_boolean
affected_modes_or_flows
related_review_cards_or_eval_cases
non_claim_boundary
```

## Candidate overlay rules

Candidate enrichment overlays may be produced only as proposed metadata overlays. They must not mutate raw/source/canonical truth.

Each overlay must carry:

```text
derived_overlay_id
source_id
proposed_field
proposed_value
basis
confidence
review_state = candidate
not_source_truth = true
```

## Tests

Create:

```text
scripts/run_main_citybrain_epoch4_data_estate_gap_routing_r1.py
tests/test_main_citybrain_epoch4_data_estate_gap_routing_r1.py
```

Tests must verify:

- all five top gap queues exist.
- no maturity score inflation.
- source-truth mutation guard passes.
- queues link back to source IDs/artifact refs where possible.
- review-card gaps are crosswalked separately from global data gaps.
- no session/fuel/training/live/forecast/action claims.


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


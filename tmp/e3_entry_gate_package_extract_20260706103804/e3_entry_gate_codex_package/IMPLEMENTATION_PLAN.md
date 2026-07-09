# Implementation Plan

## Package goal

Create a bounded Epoch 3 entry-gate implementation that reads existing empirical telemetry, publishes a baseline fuel gauge, and arms only the work that is safe to begin before trained learning or prediction.

## Sequencing

### Step 1 — Install governance artifacts

Add the canonical files:

```text
manifests/epoch3_arming_manifest.json
manifests/epoch3_arming_evaluator_spec.yaml
schemas/*.schema.json
```

Place them in the repo's governance/config path. Do not fork into multiple registries.

### Step 2 — Implement `epoch3_arming_status`

Implement as a WATCH family, dashboard panel, or equivalent standing evaluator. It should ingest aggregated metrics and evaluate the manifest's structured thresholds.

Minimum output:

```json
{
  "evaluator_id": "epoch3_arming_status",
  "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
  "status": "PASS_WITH_LIMITATIONS",
  "armed_now": [],
  "conditionally_armed": {},
  "blocked_until": {},
  "threshold_crossings": []
}
```

### Step 3 — Wire day-one exposure logging

Add or extend an `ExposureLog` object so every WATCH candidate surfaced to an operator records:

```text
watch_item_id
operator_ref
surfaced_at
surface_policy
surface_reason
deterministic_priority_tier
family_cap_state
operator_throttle_state
exploration_bucket
holdout_family_flag
ranker_component_id
ranker_score
propensity
propensity_status
selected_item_context_ref
disposition_ref
```

Records before this activates must be flagged `propensity_unknown`.

### Step 4 — Wire exploration-floor readiness

Before ranking arms, WATCH must support:

```text
exploration floor
static holdout families
exposure logging
propensity/selection metadata
ranker-off replay
operator throttle compatibility
```

### Step 5 — Add structured arming checks

Evaluate all `requires` entries with machine operations:

```text
==, !=, >=, >, <=, <, contains_all, exists, not_exists
```

The evaluator should produce failed requirement details. Do not rely on prose strings.

### Step 6 — Register offline experiments before running them

`L1.R3A_OFFLINE_RANKER_EXPERIMENT` cannot run unless the LearnedComponentRegistry contains an experimental entry with:

```text
component_kind = ranker
status = experimental
consuming_surfaces = []
training_manifest_ref present
eval_refs present
rollback_ref present
authority = offline_eval_only
```

### Step 7 — Emit ledger rows only on arming transitions

Crossing a threshold should emit:

```text
EPOCH3_ARMING_THRESHOLD_CROSSED
```

The row means the increment may begin under normal cadence. It does not auto-start work.

### Step 8 — Publish the gate atomically

The gate closeout ledger row must include:

```text
report_ref
arming_manifest_ref
evaluator_ref
hash_manifest_ref
armed_now
not_armed
status
```

The baseline report must be pinned to corpus and manifest hashes.

## Expected implementation status

The first implementation should close as:

```text
PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS
```

with:

```text
armed_now: L1.R0, L1.R1, L1.R2, L2.R1, evaluator
not_armed: L1.R3A, L1.R3B, L2.R2, L3, L4, dynamic investigation, cross-city learned transfer
```

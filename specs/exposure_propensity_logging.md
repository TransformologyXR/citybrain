# Exposure and Propensity Logging

## Principle

Exposure logging starts on day one, before trained ranking arms. The first ranker's training set begins accumulating immediately, so every surfaced WATCH item must record why the operator saw it.

## Required fields

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

## Propensity status

Allowed values:

```text
known
unknown
not_applicable
withheld_by_policy
```

Records created before logging activates must be flagged:

```text
propensity_unknown
```

## Counting policy

`propensity_unknown` records may be used for:

```text
descriptive baseline
calibration exploration
sensitivity analysis
```

They must not count toward:

```text
primary L1.R3A threshold
primary L1.R3B threshold
operator-facing ranker training manifest
```

unless an explicit override ledger row exists.

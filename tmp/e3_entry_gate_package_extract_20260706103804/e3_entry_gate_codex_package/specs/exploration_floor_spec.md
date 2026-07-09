# WATCH Exploration Floor Spec

## Purpose

Prevent feedback-loop collapse where a ranker learns only from items previously surfaced by that ranker.

## Required support before learned ranking

1. Exploration floor — fixed queue capacity reserved for non-learned/static/stratified surfacing.
2. Static holdout families — some WATCH families remain untouched by learned ranking for drift detection.
3. Exposure logging — every item records how and why it was surfaced.
4. Propensity metadata — every training candidate records selection probability/status.
5. Ranker-off replay — compare learned ranking against deterministic/static ranking on frozen slices.
6. Operator throttle compatibility — exploration must not override safety caps, family caps, or operator-controlled throttles.

## Day-one implementation target

The gate should arm infrastructure work, not learned ranking:

```text
L1.R0_WATCH_EXPLORATION_FLOOR_INFRA
```

## Minimum metrics

```text
watch.exploration_floor.enabled
watch.exploration_floor.percentage
watch.static_holdout_families.enabled
watch.static_holdout_families.count
watch.exposure_logging.coverage
ranker_off_replay.available
```

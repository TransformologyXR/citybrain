# Machine-Evaluable Thresholds

## Requirement object

Every threshold requirement must use this shape:

```json
{
  "id": "REQ_ID",
  "metric": "outcome.terminal_dispositions.count",
  "op": ">=",
  "value": 200,
  "filters": {
    "post_validation_fix": true,
    "propensity_status": "known"
  }
}
```

## Supported ops

```text
==
!=
>=
>
<=
<
contains_all
exists
not_exists
```

## Filters

Filters describe the aggregation conditions required for the metric. They are part of auditability and must travel with the evaluation result.

The evaluator may either:

1. consume pre-aggregated metrics that already applied filters, or
2. compute filtered aggregations from raw records.

It must report which strategy was used.

## Requirement result

```json
{
  "id": "R3B_TOTAL_DISPOSITIONS",
  "metric": "outcome.terminal_dispositions.count",
  "actual": 217,
  "op": ">=",
  "expected": 200,
  "passed": true,
  "filters": {
    "post_validation_fix": true,
    "propensity_status": "known"
  }
}
```

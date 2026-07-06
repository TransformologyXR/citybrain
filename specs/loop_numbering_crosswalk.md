# Loop Numbering Crosswalk

## Canonical loop map

```text
Loop 1 = outcome ledger, calibration, ranking
Loop 2 = backtest harness, forecasting
Loop 3 = causal / counterfactual
Loop 4 = institutional memory
```

## Forbidden terminology

Do not use:

```text
L3_CASE_MEMORY<underscore>LEARNING
```

Institutional memory is Loop 4 and must be referenced as:

```text
L4_CASE_MEMORY
```

Counterfactual/causal work is Loop 3 and must be referenced as:

```text
L3_COUNTERFACTUAL
```

## Drift test

A repository-level grep should fail if it finds `L3_CASE_MEMORY<underscore>LEARNING` in code, manifests, docs, tests, or ledger templates.

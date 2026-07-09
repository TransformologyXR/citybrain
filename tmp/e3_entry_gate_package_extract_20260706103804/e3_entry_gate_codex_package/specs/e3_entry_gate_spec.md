# E3 Entry Gate R1 — Fuel Gauge Spec

## Gate ID

```text
MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE
```

## Purpose

Measure the empirical fuel available at Epoch 3 entry and publish arming thresholds for learning/prediction/memory/counterfactual increments.

The gate does not create a new epoch and does not re-certify Epoch 2. It reads the fuel gauge and publishes which Epoch 3 increments are armed, conditionally armed, or blocked.

## Lanes

### Lane A — data, labels, synthetic separation

Validate:

- OutcomeRecord counts and diversity.
- Operator diversity and aggregation-floor status.
- CalibrationReport sample depth.
- WATCH volume, throttling, queue depth, and dismissal telemetry.
- Synthetic/source-class separation.
- Dubai pack training eligibility versus evaluation/demo eligibility.
- Q1–Q6 disposition policy status.

Exit:

```text
PASS if sufficient for descriptive hardening and harness work.
PASS_WITH_LIMITATIONS if descriptive work may begin but trained ranking/prediction remain blocked.
FAIL only if the gate cannot produce a trustworthy baseline fuel gauge.
```

### Lane B — scenario reality tests

Validate:

- 2–3 scenarios per mode.
- Scenario fixtures join the regression corpus.
- LLM seats stay bounded.
- WATCH caps/throttles work.
- Perception remains candidate-only.
- BRIEF does not overclaim.
- CHECK downgrades unsupported claims.

Modes:

```text
ASK
WATCH
CHECK
BRIEF
DIFF
RECALL
SPATIAL
PERCEPTION shadow
PLAN/SCHEDULE/SIMULATE fixed DAG
```

This lane is scenario replay validation, not a second human operator program.

### Lane C — prediction preconditions

Validate harness preconditions, not the completed harness:

- First forecast target selected.
- Target has real labels or enough historical proxy labels.
- Replay/event-history depth is sufficient.
- Frozen eval slice tooling can be built.
- Baseline/do-nothing comparator is defined.
- Uncertainty schema delta process is ready.
- Simulator connector inventory is honest.
- ForecastPacket remains blocked until BacktestReport exists.

## Day-one armed work

```text
L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING
L1.R0_WATCH_EXPLORATION_FLOOR_INFRA
L1.R1_OUTCOME_LEDGER_HARDENING
L1.R2_CALIBRATION_REPORT_HARDENING
L2.R1_BACKTEST_HARNESS_BUILD
E3.ARMING_STATUS_WATCH_FAMILY
```

## Not armed at gate close

```text
L1.R3A_OFFLINE_RANKER_EXPERIMENT
L1.R3B_OPERATOR_FACING_LEARNED_RANKING
L2.R2_FORECAST_MODEL
L3_COUNTERFACTUAL
L4_CASE_MEMORY
DYNAMIC_INVESTIGATION_AGENT
CROSS_CITY_LEARNED_TRANSFER
```

## Atomic publication

The gate closes only when these artifacts are published together:

```text
epoch3_arming_manifest.json
epoch3_arming_evaluator_spec.yaml
E3_FUEL_GAUGE_BASELINE_REPORT.md
hash_manifest.json
gate_ledger_row.json
```

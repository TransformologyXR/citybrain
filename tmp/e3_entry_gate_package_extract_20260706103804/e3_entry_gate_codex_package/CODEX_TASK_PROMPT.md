# Codex Task Prompt — Epoch 3 Entry Gate Fuel Gauge

You are implementing `MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE`.

## Objective

Add an Epoch 3 entry-gate fuel gauge that measures readiness for descriptive learning and harness work, publishes machine-evaluable arming thresholds, and blocks all trained/predictive/counterfactual/memory capabilities until their threshold ledger rows exist.

This is not a new epoch, not an Epoch 2 re-certification, and not a model-launch task.

## Required implementation

1. Add the arming manifest from `manifests/epoch3_arming_manifest.json` into the repo's governance/config area.
2. Add a standing evaluator named `epoch3_arming_status`.
3. Wire the evaluator to aggregated metrics from the existing telemetry/ledger surfaces where available:
   - OutcomeRecord
   - CalibrationReport
   - WatchTelemetry
   - ExposureLog
   - OperatorValidationLog
   - SyntheticManifest
   - ScenarioReplayManifest
   - ComponentRegistry
   - LearnedComponentRegistry
   - CorpusManifest
4. Implement threshold evaluation using structured `{metric, op, value, filters}` requirements, not prose strings.
5. Emit an arming ledger row when a threshold transitions from not armed to armed.
6. Ensure arming means `MAY_BEGIN_UNDER_CADENCE_NOT_STARTED`.
7. Add day-one exposure/propensity logging before ranking thresholds can count training dispositions.
8. Add exploration-floor and static-holdout readiness checks before any learned ranking can arm.
9. Register even offline ranker experiments in the LearnedComponentRegistry with `status: experimental` and `consuming_surfaces: []`.
10. Fix loop numbering: Loop 3 is counterfactual/causal; Loop 4 is institutional memory.
11. Publish gate artifacts atomically with report ref, arming manifest ref, evaluator ref, and hash manifest ref.

## Day-one armed work

The gate should arm only these items immediately:

```text
L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING
L1.R0_WATCH_EXPLORATION_FLOOR_INFRA
L1.R1_OUTCOME_LEDGER_HARDENING
L1.R2_CALIBRATION_REPORT_HARDENING
L2.R1_BACKTEST_HARNESS_BUILD
E3.ARMING_STATUS_WATCH_FAMILY
```

## Explicitly not armed

```text
L1.R3A_OFFLINE_RANKER_EXPERIMENT
L1.R3B_OPERATOR_FACING_LEARNED_RANKING
L2.R2_FORECAST_MODEL
L3_COUNTERFACTUAL
L4_CASE_MEMORY
DYNAMIC_INVESTIGATION_AGENT
CROSS_CITY_LEARNED_TRANSFER
```

## Guardrails

- Do not start learned ranking as part of this task.
- Do not start a forecast model as part of this task.
- Do not create a counterfactual model as part of this task.
- Do not create case-based institutional memory learning as part of this task.
- Do not introduce autonomous action, dispatch, legal finding, enforcement, or certified-government claims.
- Do not count `propensity_unknown` dispositions toward primary R3 arming thresholds unless an explicit override ledger row exists.
- Do not use a prose checklist as the source of truth for arming.

## Acceptance target

A successful implementation can run a local or CI smoke equivalent to:

```bash
python scripts/evaluate_arming_status.py \
  --manifest manifests/epoch3_arming_manifest.json \
  --metrics fixtures/metrics_day_one.json \
  --out /tmp/e3_arming_status_day_one.json

pytest -q tests
```

and shows:

```text
PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS
armed_now includes only L1.R0/L1.R1/L1.R2/L2.R1/evaluator work
trained ranking remains not armed until structured thresholds pass
forecasting remains blocked until BacktestReport exists
L3_COUNTERFACTUAL and L4_CASE_MEMORY are present and blocked
```

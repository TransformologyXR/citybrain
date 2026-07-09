# SPEC — R19 BMD-45 Replay Benchmark Regression Harness

## Task ID

`MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-REPLAY-BENCHMARK-REGRESSION-HARNESS-R19`

## Objective

Consume the verified R18 package and produce a repeatable BMD-45 replay benchmark/regression harness. The harness should allow future DeepStream/Metropolis runs on `txr-4070` to be compared against the R18 baseline without turning BMD-45 labels into official truth or DeepStream detections into findings.

## Required capabilities

- Validate R18 package and lineage.
- Preserve the 8-frame external-media reference set or explicitly version a new benchmark fixture set.
- Preserve source-class separation:
  - BMD-45 labels: `dataset_annotation`
  - DeepStream/Metropolis outputs: `sensor_inferred`
  - VSS: `model_generated_narrative_not_fact_source`
- Produce a replay benchmark config.
- Produce a baseline scorecard from R18 metrics.
- Produce regression assertions with tolerance bands rather than brittle exact-count mandates.
- Produce benchmark rerun instructions for `txr-4070`.
- Produce review-only failure diagnostics for drift.
- Produce final audits.

## Target status

`PASS_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_WITH_LIMITATIONS`

## Acceptable partial

`PARTIAL_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_CONTRACT_READY_RERUN_PENDING`

Use partial if the benchmark contract and scorecard are produced but the DeepStream rerun cannot execute.

## Hard exclusions

- No production live CCTV claim.
- No legal/certified finding.
- No official ticket or case.
- No dispatch/control/action.
- No identity or biometric inference.
- No VSS fact-source use.
- No treating dataset annotations as official truth.

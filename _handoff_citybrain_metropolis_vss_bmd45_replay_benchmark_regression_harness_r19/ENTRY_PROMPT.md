# ENTRY PROMPT — R19

Implement `MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-REPLAY-BENCHMARK-REGRESSION-HARNESS-R19`.

Create runner:

```text
scripts/run_main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19.py
```

Create tests:

```text
tests/test_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19
```

Input:

```text
outputs/main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18/METROPOLIS_VSS_BMD45_THRESHOLD_CALIBRATION_AND_SAMPLE_EXPANSION_R18_PACKAGE.zip
```

Expected freeze ZIP:

```text
METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_PACKAGE.zip
```

Implementation requirements:

1. Validate the R18 package, JSON/JSONL parse, and hash manifest.
2. Read R18 metrics and source-class audits.
3. Produce `BMD45_REPLAY_BENCHMARK_CONFIG_R19.json`.
4. Produce `BMD45_REPLAY_BASELINE_SCORECARD_R19.json` from the R18 baseline.
5. Produce `REPLAY_REGRESSION_ASSERTIONS_R19.json` with tolerances.
6. Optionally rerun DeepStream on `txr-4070`; if not possible, emit partial with rerun pending.
7. Produce `REGRESSION_DRIFT_REVIEW_PACKET_R19.json` explaining any drift or why rerun is pending.
8. Produce final source-class, claim-boundary, no-action, VSS-not-fact-source, and secret audits.
9. Produce `R19_CLOSEOUT_DECISION.json` and a hash manifest.

Do not package external image media. Keep external-media refs external and hash only files inside the ZIP. Dataset labels remain `dataset_annotation`; DeepStream outputs remain `sensor_inferred`. This is not a live CCTV or action workflow.

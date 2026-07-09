# ENTRY PROMPT — Spark VSS Provisioning Runbook R6E

You are implementing:

`MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-PROVISIONING-RUNBOOK-R6E`

Create a runner:

`scripts/run_main_citybrain_metropolis_vss_spark_provisioning_runbook_r6e.py`

Write outputs to:

`outputs/main_citybrain_metropolis_vss_spark_provisioning_runbook_r6e`

Freeze ZIP:

`METROPOLIS_VSS_SPARK_PROVISIONING_RUNBOOK_R6E_PACKAGE.zip`

## Purpose

Prepare the Spark-side VSS provisioning and connectivity runbook. This is not a narration task. Do not emit VSS prose unless a real configured command/endpoint is provided and explicitly probed. Even then, any returned text must be marked `model_generated_narrative` and must not be treated as fact.

## Inputs to preserve

Use the latest accepted lineage:

- R2 object metadata export PASS with 24 candidate observations and 1 candidate event.
- R6D split-host readiness partial: Spark VSS not configured, `r7_ready=false`.
- Host allocation: DeepStream/Metropolis on `txr-4070`, Spark intended for VSS, `txr-3090` inactive for this chain.

## Required outputs

Create at minimum:

- `SPARK_VSS_PROVISIONING_RUNBOOK_R6E.md`
- `SPARK_VSS_ENDPOINT_CHECKLIST_R6E.md`
- `SPARK_VSS_COMMAND_WRAPPER_CHECKLIST_R6E.md`
- `SPARK_VSS_RUNTIME_CONFIG_TEMPLATE.env.example`
- `RUNTIME_HOST_ALLOCATION_R6E.json`
- `SPARK_VSS_PROVISIONING_STATUS_R6E.json`
- `SPARK_VSS_CONNECTIVITY_PROBE_PLAN_R6E.json`
- `R7_READINESS_GATE_R6E.json`
- `R6E_CLOSEOUT_DECISION.json`
- `JSON_PARSE_REPORT_R6E.json`
- `HASH_MANIFEST.json`

## CLI/env support

Support these inputs without requiring them:

- `--spark-vss-endpoint`
- `--spark-vss-command`
- `CITYBRAIN_SPARK_VSS_ENDPOINT`
- `CITYBRAIN_SPARK_VSS_COMMAND`

If none are present:

- `runtime_configured=false`
- `probe_attempted=false`
- `probe_executed=false`
- `probe_status=NOT_CONFIGURED`
- `r7_ready=false`
- final status `PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_NOT_CONFIGURED_R6E_PROVISIONING_RUNBOOK_READY`

## Boundary

VSS is a narrator/reader only. It is not a sensor, not a detector, not a fact source, not an official record system, and not an action authority.

DeepStream/Metropolis structured detections remain the only `sensor_inferred` evidence in this lane.

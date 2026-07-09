# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

## Objective

Prepare the split-host integration contract for the Metropolis/VSS media lane while VSS is being installed on Spark.

The package should let Codex or an engineer wire the next runnable gate without changing the source boundary:

```text
DeepStream / Metropolis on txr-4070 -> sensor_inferred candidate metadata
Spark VSS runtime -> model_generated_narrative only, not a fact source
```

## Locked host allocation

```text
DeepStream / Metropolis lane:
  host: txr-4070
  status: proven by R2
  evidence: DeepStream 8.0 container, gie-kitti-output-dir, bundled sample_1080p_h264.mp4, 24 car records
  source_class: sensor_inferred

VSS lane:
  intended host: Spark / DGX Spark
  current status: installing / not yet configured
  source_class: model_generated_narrative only
  fact-source claim: forbidden

txr-3090:
  active in this chain: false
  role: data / graph / RAPIDS / heavier analytics
```

## Scope

R6D may create:

- split-host allocation artifact
- Spark VSS endpoint/command configuration template
- cross-host payload contract
- R7 readiness gate contract
- network/connectivity probe schema
- safe environment template
- acceptance checks

R6D must not:

- emit VSS narration
- fabricate VSS output
- modify R2 candidate observations/events
- claim VSS is running before a real probe passes
- create an official record, ticket, alert, dispatch, route, enforcement action, or legal finding

## PASS / PARTIAL logic

R6D is a handoff/readiness package. It can be considered complete when the handoff package validates.

A later runtime gate may PASS only if:

```text
spark_vss_runtime_configured = true
spark_vss_probe_attempted = true
spark_vss_probe_executed = true
spark_vss_probe_status = SUCCESS
r7_ready = true
```

If Spark VSS remains unconfigured, the runtime gate must remain partial.

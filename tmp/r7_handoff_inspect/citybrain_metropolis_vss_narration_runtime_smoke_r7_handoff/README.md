# CityBrain Metropolis/VSS — R7 Narration Runtime Smoke Handoff

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7`

This handoff opens R7 only because R6C is now reported as:

`PASS_METROPOLIS_VSS_RUNTIME_PROVISIONED_AND_CONNECTED_R6C`

R7 is the first **actual Spark VSS narration smoke**. It is not a production monitoring
task, not a legal finding task, and not a control/action task.

## Locked host allocation

```text
txr-4070:
  DeepStream / Metropolis
  source_class = sensor_inferred
  R2 proven: DeepStream 8.0 + gie-kitti-output-dir + sample_1080p_h264.mp4
  24 car records -> vehicle_presence_candidate -> 1 candidate event

Spark / DGX Spark:
  VSS runtime host
  R6C readiness endpoint: http://spark-2445:38111/v1/ready
  source_class = model_generated_narrative_only_not_fact_source

txr-3090:
  not active in this Metropolis/VSS chain
```

## R7 principle

DeepStream/Metropolis remains the fact basis for candidate metadata.
VSS output is attached only as a narration sidecar with source class
`model_generated_narrative`.

R7 may PASS only if a real Spark VSS call executes and emits a usable narration
record without modifying candidate events or creating any official/action record.

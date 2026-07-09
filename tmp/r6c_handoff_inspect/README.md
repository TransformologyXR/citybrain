# CityBrain Metropolis/VSS Runtime Provisioning and Configuration R6C Handoff

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-PROVISIONING-AND-CONFIGURATION-R6C`

This handoff exists because R3, R4, R5, R6, and R6B correctly remained guarded partials: no real VSS command or endpoint is configured.

R6C is not a narration task. It is a provisioning/configuration task.

## Goal

Create a safe, repeatable way to configure a real VSS runtime as either:

1. endpoint mode: `CITYBRAIN_VSS_ENDPOINT`
2. command mode: `CITYBRAIN_VSS_COMMAND`

Then prove the configured runtime can be safely probed.

## Hard gate

`MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7` must remain blocked until R6C or R6B reaches PASS with a real configured runtime.

## Boundary

DeepStream/Metropolis remains `sensor_inferred`.
VSS remains `model_generated_narrative` only and is not a fact source.

No narration may be fabricated.
No candidate event may be modified.
No official record/action may be created.

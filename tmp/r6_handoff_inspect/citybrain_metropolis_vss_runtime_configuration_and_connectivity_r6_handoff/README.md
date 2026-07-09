# CityBrain Metropolis / VSS — Runtime Configuration and Connectivity R6 Handoff

Task:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6
```

This handoff follows R5, which remained a clean guarded partial because no VSS runtime command or endpoint was configured.

R6 is **not another narration task**. R6 is the narrow configuration/connectivity gate required before another narration smoke is meaningful.

## Goal

Prove whether a real VSS runtime is available and safely invokable through a configured command or endpoint.

## Core rule

Do not fabricate VSS output. If no VSS runtime is configured, emit a partial status and stop.

## Expected runner

```text
scripts/run_main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6.py
```

## Expected output root

```text
outputs/main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6
```

## Expected freeze ZIP

```text
METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip
```

## Important boundary

DeepStream/Metropolis R2 object metadata remains the only `sensor_inferred` source. VSS is still only allowed as `model_generated_narrative` after a real runtime is configured and executed.

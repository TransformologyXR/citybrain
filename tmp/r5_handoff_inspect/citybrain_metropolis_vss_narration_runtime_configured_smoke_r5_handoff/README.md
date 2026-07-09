# CityBrain Metropolis/VSS Narration Runtime Configured Smoke R5 Handoff

Task:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-CONFIGURED-SMOKE-R5
```

This handoff moves the Metropolis/VSS lane from the R4 guarded partial into a
configured-smoke gate. R5 should attempt a real VSS command or endpoint when one
is configured, normalize only the resulting prose as `model_generated_narrative`,
and prove that VSS narration remains separate from DeepStream/Metropolis
`sensor_inferred` object metadata.

R5 must never fabricate narration. If no runtime command or endpoint is configured,
the correct final status is:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R5_GUARDRAILS_READY
```

R5 is still bounded local/sample-media review evidence, not production monitoring.

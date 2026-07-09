# BOUNDARY POLICY — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

## Allowed

R6 may output:

- runtime configuration status
- redacted command/endpoint mode
- connectivity probe status
- runtime availability/readiness decision
- timeout and error evidence
- safe stdout/stderr/response snippets
- CHECK runtime sufficiency report
- human-readable limitations

## Not allowed

R6 may not output:

- confirmed violation
- legal/certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement command
- alert as operational command
- automated action
- new candidate observations
- new sensor facts
- fabricated VSS narration

## Source class rule

```text
DeepStream / Metropolis structured metadata = sensor_inferred
VSS runtime output = model_generated_narrative
R6 connectivity metadata = runtime_configuration_evidence
```

VSS output must never replace or override DeepStream/Metropolis metadata.

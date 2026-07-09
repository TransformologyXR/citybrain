# BOUNDARY POLICY — R6C

The Metropolis/VSS lane is candidate-observation only.

Allowed:

- runtime configuration discovery;
- redacted command/endpoint reporting;
- bounded connectivity probes;
- readiness gate for later narration.

Not allowed:

- confirmed violation;
- legal or certified finding;
- identity or biometric inference;
- official case/ticket creation;
- dispatch/routing/control/enforcement;
- alert as operational command;
- automated action;
- VSS as a sensor/fact source;
- fabricated narration.

Source-class rule:

```text
DeepStream / Metropolis structured detections = sensor_inferred
VSS output = model_generated_narrative_only_not_fact_source
```

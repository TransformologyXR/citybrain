# BOUNDARY POLICY

R6B is a connectivity gate, not a narration or detection milestone.

Allowed outputs:

- runtime configured / not configured
- endpoint or command reachable / unreachable
- latency / exit code / HTTP status
- redacted excerpts
- connectivity limitations
- next-step recommendation

Forbidden outputs:

- confirmed violation
- legal finding
- identity / biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- alert as operational command
- VSS-derived fact source
- VSS-derived new detection/count/location/timestamp
- candidate event mutation

Source classes remain:

```text
DeepStream / Metropolis structured metadata = sensor_inferred
VSS runtime text = model_generated_narrative only, and only in later narration tasks
Official records = official_record only when sourced from official systems
```

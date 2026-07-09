# ACCEPTANCE CHECKS — R7

## Required PASS checks

- R6C lineage is PASS
- host allocation matches R6C truth
- Spark VSS readiness probe PASS
- VSS summarize/command runtime attempted
- VSS summarize/command runtime executed
- exactly one bounded VSS request created
- at least one narration sidecar emitted
- narration source class is `model_generated_narrative`
- R2 DeepStream/Metropolis observations remain `sensor_inferred`
- R2 candidate event is unchanged
- no official record created
- no action created
- no identity/biometric claim
- no legal/violation finding
- no dispatch/routing/control/enforcement command
- secret audit PASS
- hash manifest PASS
- JSON/JSONL parse PASS

## Required partial statuses

Use a partial status if VSS cannot be safely called or produces no usable narration:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SUMMARIZE_ROUTE_NOT_CONFIGURED
PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_MEDIA_ACCESS_BLOCKED
PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_RUNTIME_ERROR_GUARDRAILS_READY
PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_EMPTY_OUTPUT_GUARDRAILS_READY
PARTIAL_METROPOLIS_VSS_NARRATION_SMOKE_R7_MALFORMED_OUTPUT_GUARDRAILS_READY
```

## Required FAIL statuses

Use FAIL if safety/source boundaries are violated:

```text
FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SOURCE_CLASS_BOUNDARY_BROKEN
FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_EVENT_MUTATION
FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_FORBIDDEN_CLAIM
FAIL_METROPOLIS_VSS_NARRATION_SMOKE_R7_SECRET_EXPOSURE
```

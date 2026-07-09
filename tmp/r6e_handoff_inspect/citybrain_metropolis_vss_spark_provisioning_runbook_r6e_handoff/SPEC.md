# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-PROVISIONING-RUNBOOK-R6E

## Objective

Create a Spark-side VSS provisioning/configuration runbook and readiness gate so the VSS install team can expose a safe command or endpoint without changing the R2 DeepStream/Metropolis evidence chain.

R6E is a provisioning/readiness package only. It must not claim VSS runtime execution unless a real command or endpoint is supplied and probed.

## Scope

In scope:

- Spark VSS environment checklist
- endpoint contract
- command-wrapper contract
- payload contract from R2/R6D into VSS
- smoke-test command examples
- redacted runtime config template
- R7 readiness criteria
- no-fabrication / no-action guardrails

Out of scope:

- running VSS narration
- changing R2 candidate observations/events
- official/legal/violation conclusions
- identity or biometric inference
- dispatch, routing, control, enforcement, alerts as commands
- use of `txr-3090` for this chain

## Host allocation

```text
txr-4070:
  DeepStream / Metropolis
  source_class = sensor_inferred
  status = proven_by_R2

Spark / DGX Spark:
  VSS intended host
  source_class = model_generated_narrative_only_not_fact_source
  status = installing / not_configured until probe passes

txr-3090:
  not active in this chain
```

## Status rules

PASS is allowed only if:

- Spark VSS command or endpoint is supplied
- probe is attempted
- probe executes successfully
- response shape is safe and bounded
- R7 readiness gate is true
- no secret leakage
- no narration is fabricated
- no candidate event is mutated

PARTIAL is required if:

- no command/endpoint is configured
- endpoint unreachable
- command missing executable/runtime/model
- response shape cannot be interpreted safely

FAIL is required if:

- secrets are leaked
- output claims detection/fact-source authority for VSS
- VSS modifies candidate observations/events
- official/legal/action/identity claims appear

# ACCEPTANCE CHECKS — R6E

## PASS

R6E may PASS only when all are true:

- Spark VSS command or endpoint configured
- probe attempted and executed
- probe status `SUCCESS`
- response is bounded and safe
- secrets redacted
- R7 readiness gate true
- no narration fabrication
- no candidate-event mutation
- no official/action/identity/legal claims

## PARTIAL

Expected while Spark is still installing:

- no endpoint or command configured
- probe not attempted
- `r7_ready=false`
- final status `PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_NOT_CONFIGURED_R6E_PROVISIONING_RUNBOOK_READY`

## FAIL

Fail immediately if:

- VSS is described as `sensor_inferred`
- VSS output is treated as fact source
- candidate event is modified by VSS
- official record, ticket, alert command, enforcement, dispatch, routing, identity, or legal conclusion is created
- secrets are written to artifacts

# ACCEPTANCE CHECKS — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

## PASS path

Use:

```text
PASS_METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_WITH_LIMITATIONS
```

Required evidence:

- R5 package validation PASS
- runtime configured = true
- selected runtime mode = command or endpoint
- connectivity probe attempted = true
- connectivity probe executed = true
- probe result = PASS
- runtime metadata captured safely
- secret audit PASS
- source-class audit PASS
- claim-boundary audit PASS
- no-action audit PASS
- JSON parse PASS
- hash manifest PASS

## Guarded partial: not configured

Use:

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6_CONNECTIVITY_CONTRACT_READY
```

Allowed when:

- no command or endpoint is configured
- no runtime is attempted
- no narration is fabricated
- all guardrails/audits pass

## Guarded partial: configured but failed

Use:

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_CONNECTIVITY_FAILED_R6
```

Allowed when:

- command/endpoint is configured
- runtime probe is attempted
- probe fails, times out, or returns invalid response
- no boundary is breached
- no narration is fabricated

## FAIL

Use:

```text
FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_BOUNDARY_BREACH_R6
```

If any of these happen:

- VSS is treated as a sensor/fact source
- candidate event is modified by VSS
- candidate observations/detections are invented
- official record/ticket/action is created
- identity/biometric inference appears
- confirmed violation/legal finding appears
- dispatch/routing/control/enforcement/action command appears
- secrets are logged
- external endpoint is used without explicit config and audit trail

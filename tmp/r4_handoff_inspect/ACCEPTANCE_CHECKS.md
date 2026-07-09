# ACCEPTANCE CHECKS — R4

## PASS gate

R4 may pass only if all are true:

- input R3 package validates
- R3 preserved R2 package truth
- VSS runtime is configured
- VSS runtime is attempted and executed
- at least one narration sidecar record is emitted
- all narration sidecars use `source_class = model_generated_narrative`
- VSS is not treated as fact source
- candidate event is not modified by VSS
- object count remains sourced from R2
- no new object classes are invented by VSS
- no identity/face/plate/biometric claims
- no confirmed violation/legal/certified finding
- no official case/ticket
- no dispatch/routing/control/enforcement/action
- no production monitoring/live CCTV claim
- JSON and JSONL parse passes
- hash manifest verifies
- secret audit passes

Expected PASS status:

```text
PASS_METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_WITH_LIMITATIONS
```

## Partial gate

Use partial if:

- VSS command/endpoint is still not configured;
- VSS times out;
- VSS executes but returns no usable narration;
- VSS output is unavailable but all guardrails/contracts are ready.

Do not fabricate narration text.

## Fail gate

Use fail if:

- input R3 package cannot be validated;
- source-class separation drifts;
- VSS becomes or is treated as a sensor/fact source;
- VSS output modifies the candidate event;
- VSS output contains forbidden legal/identity/action/production claims;
- package parse/hash/secret checks fail.

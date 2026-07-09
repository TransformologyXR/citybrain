# ACCEPTANCE CHECKS — R5

## R4 input validation

- ZIP opens
- JSON parse PASS
- JSONL parse PASS
- hash manifest PASS
- R4 status is guarded partial, not FAIL
- R2 candidate observations/events are preserved as 24/1
- R2 source class remains `sensor_inferred`

## Runtime configuration

PASS path requires one of:

- `--vss-command`
- `--vss-endpoint`
- `CITYBRAIN_VSS_COMMAND`
- `CITYBRAIN_VSS_ENDPOINT`

If none exists, R5 must close as partial-not-configured and emit zero narration.

## Runtime execution

PASS path requires:

- attempted = true
- executed = true
- return code or HTTP status captured
- stdout/stderr/response references captured or explicitly null
- command/endpoint redacted in package artifacts
- timeout applied

## Narration normalization

PASS path requires at least one normalized sidecar with:

- `source_class = model_generated_narrative`
- candidate event reference
- evidence bundle reference
- prose text
- uncertainty or limitation wording
- human review required
- not a finding
- no action taken

## Boundary audits

All must PASS:

- source-class separation
- VSS guardrail
- prose-vs-detection conflict
- claim-boundary
- no-action
- secret

## Forbidden content

R5 fails if VSS output or package claims:

- confirmed violation
- legal/certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- alert as operational command
- autonomous action
- production monitoring
- live CCTV deployment
- new detections or counts created by VSS

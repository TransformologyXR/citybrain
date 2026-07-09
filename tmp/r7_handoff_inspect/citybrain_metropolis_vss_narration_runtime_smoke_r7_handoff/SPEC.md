# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7

## Objective

Run the first bounded Spark VSS narration runtime smoke against the already-proven
R2 Metropolis/DeepStream candidate event context.

## Inputs

Required input lineage:

- R2 object metadata export package
- R2 sample media reference: `container bundled samples/streams/sample_1080p_h264.mp4`
- R2 candidate observations: 24
- R2 candidate event count: 1
- R6C connectivity PASS proving Spark VSS readiness endpoint reachable from txr-4070
- Spark VSS readiness endpoint: `http://spark-2445:38111/v1/ready`

## Scope

Use exactly:

```text
one media file/feed
one candidate event
one narration request
one Spark VSS runtime host
one VSS narration sidecar
```

## Allowed output

R7 may output:

- VSS runtime request metadata
- VSS runtime response metadata
- VSS narration sidecar
- model-generated summary/prose
- model-generated timestamp/event references
- prose-vs-detection conflict audit
- source separation audit
- CHECK narration sufficiency report
- human-review note

## Forbidden output

R7 must not output:

- confirmed violation
- legal/certified finding
- official case/ticket
- identity or biometric inference
- dispatch/routing/control/enforcement
- alert as operational command
- automated action
- VSS-derived detection counts as fact
- VSS modifications to R2 candidate event truth

## Source classes

```text
DeepStream / Metropolis structured detections = sensor_inferred
VSS narration = model_generated_narrative
official records = out of scope
```

## PASS criteria

Status may be `PASS_METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_WITH_LIMITATIONS` only if:

- R6C PASS lineage is present
- Spark VSS readiness probe succeeds
- a real VSS summarization/narration call is attempted and executed
- at least one narration sidecar record is emitted
- VSS output is tagged `model_generated_narrative`
- R2 candidate event remains unchanged
- no official/action record is created
- source-class, guardrail, claim-boundary, no-action, secret, and conflict audits pass

## Partial criteria

Return a partial status if:

- Spark readiness passes but summarize route/command is missing
- VSS call fails but guardrails remain intact
- VSS output is empty, malformed, or unusable
- media cannot be accessed by Spark
- API contract is unclear and no safe wrapper is supplied

## FAIL criteria

Return FAIL if:

- VSS prose is promoted to fact source
- R2 candidate event is mutated by VSS
- identity/legal/action/official-record claims are emitted
- secrets are written to artifacts
- unaudited narration is accepted

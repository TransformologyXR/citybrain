# MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-INTEGRATION-READINESS-REVIEW

## Objective

Validate that the governed runtime trace harness and decision-support demo polish lanes can be consumed together without semantic drift, boundary drift, or packet-shape mismatch.

This is a read-only integration readiness review. It must not implement a new runtime, new UI, new simulator, new agent loop, or any action/execution path.

## Required upstreams

Discover and require green statuses for:

- `MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-CLOSEOUT` or latest green closeout/freeze for the governed runtime trace harness lane.
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-POLISH-CLOSEOUT` or latest green closeout/freeze for the demo polish lane.
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH` from the prior decision-support sprint.
- Track S/B/R/I/C outputs as available through the latest certified-state/handover refresh.

If any required upstream is missing or not green, fail safely.

## Required checks

Validate:

- Runtime trace stages align to the governed 9-stage contract without creating nine LLM gates.
- Demo polish consumes trace/evidence/option-set/HITL/cascade facts without redefining them.
- `reviewed_option_set` schema remains unchanged.
- Track D remains authoritative for HITL proposal lifecycle after promotion.
- Decision-support outputs preserve `execution_state = not_executed` unless explicitly and safely represented as inert/stub context.
- Do-nothing baseline remains visible.
- Abstain/no-safe-option representation remains visible.
- SUMO refs remain labelled as context, not certified traffic truth.
- Similar-case refs remain labelled as context, not precedent mandates.
- Cross-domain cascade refs remain labelled as context, not certified impact propagation.
- No production/public/API/live-monitoring/action claim appears.

## Expected output root

`outputs/main_citybrain_d6_runtime_trace_demo_polish_integration_readiness_review/`

## Expected files

- `MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `INTEGRATION_READINESS_MATRIX.json`
- `TRACE_TO_DEMO_POLISH_ALIGNMENT.json`
- `OPTION_SET_CONTRACT_PRESERVATION_REVIEW.json`
- `HITL_BOUNDARY_CARRY_FORWARD_REVIEW.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## PASS status

`PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS`

## FAIL status

`FAIL_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW`

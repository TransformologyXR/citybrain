# Track S checklist

## Before running
- [ ] Confirm repo root is `C:\Users\hazem\Documents\CityBrain`.
- [ ] Confirm `outputs/main_citybrain_d6_r2_certified_state_and_handover_refresh` exists.
- [ ] Confirm Track D HITL freeze exists.
- [ ] Confirm R2 demo freeze/final package review exists.
- [ ] Confirm no production/action claims are introduced.

## S1 Option-set contract
- [ ] Defines `reviewed_option_set`.
- [ ] Defines `candidate_option`.
- [ ] Includes mandatory do-nothing baseline.
- [ ] Includes abstain/no-safe-option state.
- [ ] Includes `schema_version` on set and option.
- [ ] Defines Track D proposal composition.
- [ ] Defines D4Y decision-support relationship.
- [ ] Produces example fixtures.
- [ ] Produces validation report and audits.

## S2 9-stage runtime interface
- [ ] Defines RECALL.
- [ ] Defines PLAN.
- [ ] Defines VALIDATE_PLAN.
- [ ] Defines EXECUTE as local sim/optimizer/retrieval execution only.
- [ ] Defines NORMALIZE.
- [ ] Defines SYNTHESIZE as the only narration stage.
- [ ] Defines RESOLVE_ACTIONS.
- [ ] Defines SUGGEST.
- [ ] Defines COMPLETE.
- [ ] Explicitly rejects nine-LLM/agent-swarm interpretation.

## S3 Hero corridor action enum
- [ ] Defines allowed review-only action types.
- [ ] Defines blocked action types.
- [ ] Defines promotion eligibility.
- [ ] Defines Track D mapping.
- [ ] Keeps execution state not_executed.

## S4 Golden quality gate
- [ ] Tests do-nothing baseline present.
- [ ] Tests abstain/no-safe-option.
- [ ] Tests dominated option detection.
- [ ] Tests missing obvious option detection.
- [ ] Tests stale scenario state.
- [ ] Tests Track D proposal ownership.
- [ ] Tests unsafe auto-execute blocking.
- [ ] Tests comparison-axis consistency.

## S5 Closeout
- [ ] Verifies all S1-S4 outputs.
- [ ] Consolidates schemas and contracts.
- [ ] Verifies boundary/no-action/no-mutation/secret/hash.
- [ ] Recommends Plan Mode/SUMO and Similar Case Retrieval as next lanes.

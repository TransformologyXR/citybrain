# ENTRY PROMPT — Track I Inverse Dynamics / Multi-Option Decision Support

You are continuing CityBrain after Track S, Track B, Track R, and Track D are green.

Run this package as one sequential Codex thread.

## Objective

Implement the bounded, local/replay-only inverse-dynamics multi-option decision-support lane.

This lane consumes:
- Track S reviewed_option_set and candidate_option contracts
- Track B Plan Mode / SUMO green scenario output
- Track R similar-case retrieval attachments
- Track D HITL proposal lifecycle contract
- R2 certified-state/handover refresh

It must produce 2–3 human-reviewable candidate options plus the mandatory do-nothing baseline where possible, compare their predicted tradeoffs, preserve abstain/no-safe-option behavior, and map eligible options to Track D proposal references only as promotion candidates.

## Execution order

1. `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-DECISION-SUPPORT-PREFLIGHT`
2. `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-GENERATOR-R1`
3. `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-TRADEOFF-EVALUATION-R2`
4. `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-HITL-PROMOTION-BRIDGE-R3`
5. `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-CLOSEOUT`
6. Optional, only if closeout is green: `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-MILESTONE-FREEZE`

## Boundary

This is local/replay review/query context only.

No execution, no dispatch, no routing/control, no enforcement, no public alert, no official ticket/case, no legal/certified/confirmed finding, no automated action, no production/public API claim.

## Success definition

The lane closes only if:
- required upstreams are found and green
- option/proposal boundary is preserved
- do-nothing baseline is present where options are available
- abstain/no-safe-option cases are preserved
- reviewed_option_set schema is respected
- Track B simulation refs are attached
- Track R similar-case refs are attached
- Track D promotion mapping is non-authoritative until human review
- all generated option sets pass golden quality checks
- claim/no-action/no-mutation/secret/hash audits pass

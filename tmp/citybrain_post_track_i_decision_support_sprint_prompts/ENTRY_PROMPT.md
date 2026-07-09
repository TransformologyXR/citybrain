# ENTRY PROMPT — Post Track I Decision-Support Sprint

Use this pack only after Track I is green:

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_WITH_LIMITATIONS`

Current upstream chain expected:
- Track S: `PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS`
- Track B: `PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS`
- Track R: `PASS_MAIN_CITYBRAIN_D6_SIMILAR_CASE_RETRIEVAL_CLOSEOUT_WITH_LIMITATIONS`
- Track I: `PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_WITH_LIMITATIONS`

Goal:
Close the current decision-support sprint by validating that contract, forward dynamics, similar-case retrieval, inverse dynamics, HITL promotion boundaries, and control-room/demo packaging align around one shared hero corridor scenario.

Run sequence:
1. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONVERGENCE-READINESS-REVIEW`
2. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-R1`
3. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-CLOSEOUT-R1`
4. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-MILESTONE-FREEZE`
5. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH`

Do not skip the convergence review.

Boundary:
- Local/replay review/query context only.
- No production/public API claim.
- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified/confirmed finding, automated action, or live action.
- Track D remains authoritative for proposal lifecycle after human promotion.
- reviewed_option_set options are pre-review decision-support candidates, not executed actions.
- execution_state must remain not_executed unless a separately gated future policy explicitly changes it.
- 9-stage runtime is a governed state machine, not nine autonomous LLM gates; SYNTHESIZE is the only grounded narration stage.


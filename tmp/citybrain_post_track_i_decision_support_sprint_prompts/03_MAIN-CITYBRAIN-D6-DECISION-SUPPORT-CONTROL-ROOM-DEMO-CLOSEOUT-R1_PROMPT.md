# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-CLOSEOUT-R1

Task:
Close out the Decision-Support Control Room Demo R1 and verify it is consistent with the convergence review and upstream Track S/B/R/I artifacts.

Required upstream:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-R1`

Validate:
- demo manifest parses
- reviewed_option_set facts reconciled
- do-nothing baseline disclosed
- abstain/no-safe-option support disclosed
- candidate options not promoted unless explicit Track D refs exist
- proposal refs remain Track D-owned
- simulated outputs labelled simulated/context
- similar-case outputs labelled precedent/context only
- no execution
- all limitations disclosed
- audits pass

Expected output root:
`outputs/main_citybrain_d6_decision_support_control_room_demo_closeout_r1/`

Expected status:
`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS`

Expected files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `ACCEPTANCE_MATRIX.json`
- `DEMO_FACT_RECONCILIATION.json`
- `BOUNDARY_REVIEW.json`
- `LIMITATIONS_REVIEW.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Boundary:
- Local/replay review/query context only.
- No production/public API claim.
- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified/confirmed finding, automated action, or live action.
- Track D remains authoritative for proposal lifecycle after human promotion.
- reviewed_option_set options are pre-review decision-support candidates, not executed actions.
- execution_state must remain not_executed unless a separately gated future policy explicitly changes it.
- 9-stage runtime is a governed state machine, not nine autonomous LLM gates; SYNTHESIZE is the only grounded narration stage.


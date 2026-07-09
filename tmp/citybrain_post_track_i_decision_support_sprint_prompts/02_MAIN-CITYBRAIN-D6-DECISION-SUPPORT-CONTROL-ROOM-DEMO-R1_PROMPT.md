# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTROL-ROOM-DEMO-R1

Task:
Compose a bounded decision-support control-room demo package from the green convergence review.

This is a demo/package task, not new platform implementation.

Required upstream:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONVERGENCE-READINESS-REVIEW`

Demo should show:
- shared hero corridor scenario
- reviewed_option_set with do-nothing baseline
- 2-3 candidate options if present
- abstain/no-safe-option support if applicable
- SUMO forward-dynamics context
- inverse-dynamics option generation context
- similar-case attachments
- HITL promotion boundary
- no execution state
- operator, planner, executive, analyst persona summaries if Track P assets are available
- Omniverse/web companion references if available

Expected output root:
`outputs/main_citybrain_d6_decision_support_control_room_demo_r1/`

Expected status:
`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_R1_WITH_LIMITATIONS`

Expected files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `DECISION_SUPPORT_DEMO_MANIFEST.jsonl`
- `REVIEWED_OPTION_SET_DEMO_SUMMARY.json`
- `OPERATOR_WALKTHROUGH.md`
- `EXECUTIVE_WALKTHROUGH.md`
- `PLANNER_WALKTHROUGH.md`
- `ANALYST_WALKTHROUGH.md`
- `OMNIVERSE_HANDOFF_SUMMARY.md`
- `WEB_COMPANION_SUMMARY.md`
- `HITL_PROMOTION_BOUNDARY_SUMMARY.md`
- `LIMITATIONS_AND_CLAIM_LABELS.md`
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


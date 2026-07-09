# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH

Task:
Refresh the certified-state and handover ledger after the decision-support milestone freeze.

Required upstream:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-MILESTONE-FREEZE`

Produce:
- updated certified-state summary
- closed track list
- ready-next track list
- deferred/not-claimed list
- frozen counts and limitations
- stale recommendation detection
- next-track recommendation

Expected output root:
`outputs/main_citybrain_d6_decision_support_certified_state_and_handover_refresh/`

Expected status:
`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS`

Recommended next candidates to evaluate, not necessarily start:
- inverse-dynamics R2/R3 extension if initial Track I was limited
- cross-domain cascade preflight
- perception candidate-observation spike
- decision-support collateral package
- production/security preflight only if stakeholder deployment requires it

Expected files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json`
- `CERTIFIED_STATE_SUMMARY.md`
- `HANDOVER_BRIEF.md`
- `CLOSED_TRACK_LEDGER.json`
- `READY_NEXT_TRACKS.json`
- `DEFERRED_NOT_CLAIMED_REGISTER.json`
- `STALE_RECOMMENDATION_DETECTION.json`
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


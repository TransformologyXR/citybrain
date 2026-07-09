# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONVERGENCE-READINESS-REVIEW

Task:
Validate that Track S, Track B, Track R, and Track I can be composed into one coherent decision-support layer without schema drift, lifecycle drift, or boundary drift.

Required upstreams:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE`
- `MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2`

Validate:
- reviewed_option_set schema compatibility
- candidate_option schema compatibility
- option/proposal boundary
- Track D ownership after promotion
- do-nothing baseline present
- abstain/no-safe-option states preserved
- comparison axes consistent
- SUMO simulation refs attached but not certified
- similar-case refs attached but not precedent mandates
- inverse-dynamics options are human-review candidates only
- no execution or dispatch is possible
- golden quality gate findings are carried forward
- one shared hero corridor scenario is used

Expected output root:
`outputs/main_citybrain_d6_decision_support_convergence_readiness_review/`

Expected status:
`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONVERGENCE_READINESS_REVIEW_WITH_LIMITATIONS`

Expected files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONVERGENCE_READINESS_REVIEW_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `CONVERGENCE_MATRIX.json`
- `OPTION_SET_COMPATIBILITY_REPORT.json`
- `TRACK_D_BOUNDARY_COMPATIBILITY_REPORT.json`
- `SUMO_AND_INVERSE_DYNAMICS_COMPATIBILITY_REPORT.json`
- `SIMILAR_CASE_ATTACHMENT_COMPATIBILITY_REPORT.json`
- `GOLDEN_QUALITY_GATE_CARRY_FORWARD.json`
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


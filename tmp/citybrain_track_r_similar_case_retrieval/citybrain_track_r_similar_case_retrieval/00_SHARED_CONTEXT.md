# Shared CityBrain Context for Decision-Support Intelligence Tracks

Current accepted entry point:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

Reported status:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS`

The track produced:
- `reviewed_option_set` schema
- `candidate_option` schema
- option/proposal composition rules
- D4Y decision-support relationship notes
- governed 9-stage runtime interface
- model usage policy
- trace/audit contract
- hero corridor reviewed-action enum
- blocked-action enum
- Track D mappings
- consolidated contract index
- golden quality gate

Core contract rules:
- Option is not Proposal.
- `candidate_options[]` are pre-review candidates.
- `proposal_refs[]` may point to Track D HITL proposal objects only after human promotion.
- Track D remains authoritative for approval/reject/modify/request-more-evidence/audit/lifecycle state.
- `review_state_rollup` is display/mirror only.
- `execution_state` remains `not_executed`.
- A do-nothing baseline is mandatory when options are available.
- Abstain/no-safe-option is a first-class outcome.
- `schema_version`, `valid_as_of`, `scenario_state_ref`, generator/simulation provenance, and comparison axes must be preserved.

Shared hero scenario:

`scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001`

Use the bounded LON hero neighbourhood / corridor replay context. This is the same scenario used by the Hero control-room demo, Real USD Twin Track A, HITL Track D, and the decision-support contract spine. Do not invent a second unrelated scenario.

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.

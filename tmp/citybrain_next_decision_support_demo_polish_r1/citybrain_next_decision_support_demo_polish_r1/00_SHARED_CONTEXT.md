# Shared context

Current certified upstream:
`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS`

The Decision-Support sprint is closed green. It includes:
- Track S Decision-Support Contract Spine
- Track B Plan Mode / SUMO
- Track R Similar-Case Retrieval
- Track I Inverse Dynamics / Multi-Option Decision Support
- Track C Cross-Domain Cascade
- Operator Decision-Support Surface R1
- Governed 9-Stage Runtime Contract Smoke R1
- Decision-Support cascade integration, collateral, final package review, and sprint handover

Core invariants:
- `reviewed_option_set` is the decision-support output contract.
- `candidate_option` is not a Track D proposal.
- Track D remains authoritative after human promotion.
- `execution_state` remains `not_executed` unless a future separately gated task says otherwise.
- Do-nothing baseline and abstain/no-safe-option remain first-class.
- SUMO, similar-case, inverse-dynamics, and cascade refs are context/evidence, not mandates.
- Governed 9-stage runtime is a state machine, not nine autonomous LLM gates.
- Exactly one grounded narration step may exist where needed; deterministic truth remains code/evidence-first.

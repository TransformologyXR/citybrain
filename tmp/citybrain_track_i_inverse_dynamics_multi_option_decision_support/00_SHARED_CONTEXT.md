# Shared Context — Track I Inverse Dynamics / Multi-Option Decision Support

Current validated upstream state:
- Track S Decision-Support Contract Spine is green.
- Track B Plan Mode / SUMO is green and produced at least one green scenario output.
- Track R Similar-Case Retrieval is green and attached similar cases to reviewed option sets.
- Track D HITL Reviewed Action is green and remains authoritative for proposal approval lifecycle.
- R2 certified-state / handover refresh is green.

Track I purpose:
Given a desired outcome for the shared hero corridor scenario, generate a bounded set of human-reviewable candidate options, compare predicted tradeoffs, attach evidence/simulation/similar-case provenance, and optionally prepare promotion mappings into Track D HITL proposal lifecycle.

Track I must not:
- execute actions
- dispatch teams
- alter live routing or signals
- enforce or issue tickets
- create official cases
- publish public alerts
- make legal/certified/confirmed findings
- claim production/public API readiness
- claim autonomous monitoring or control

Load-bearing rules:
1. Option is not Proposal.
2. Track D remains authoritative after promotion.
3. `reviewed_option_set` remains the normalized output shape.
4. Do-nothing baseline is mandatory.
5. Abstain/no-safe-option is first-class.
6. All execution states remain `not_executed`.
7. Use the same shared hero corridor scenario.
8. Similar cases are advisory evidence context, not authority.
9. Any generator output must pass the Track S golden quality gate before closeout.
10. 9-stage runtime remains a governed state machine, not nine LLM gates.

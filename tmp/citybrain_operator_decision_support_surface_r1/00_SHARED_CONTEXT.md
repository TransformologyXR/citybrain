# Shared Context — Decision-Support Intelligence Sprint

You are continuing CityBrain after the R2 certified-state/handover refresh and after the Decision-Support Contract Spine, Plan Mode/SUMO, Similar-Case Retrieval, Inverse Dynamics, and Decision-Support convergence/demo/freeze/handover sequence.

Current sprint definition:
- This sprint includes the Decision-Support Intelligence work plus Cross-Domain Cascade and the approved surface/contract/final-package closure that follows.
- Cross-Domain Cascade is currently running separately.
- Do not run this package until `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-MILESTONE-FREEZE` or its accepted closeout/freeze equivalent is green, unless explicitly instructed to run as a read-only preflight only.

Core frozen truths to preserve:
- `reviewed_option_set` is the normalized downstream contract.
- Candidate option is not Track D proposal.
- Track D remains authoritative after promotion into the HITL proposal lifecycle.
- Execution state remains `not_executed` unless a future separately gated human-approved workflow exists.
- Do-nothing baseline and abstain/no-safe-option states must remain first-class.
- SUMO references are context-labelled and not certified traffic truth.
- Similar-case references are context-labelled and not precedent mandates.
- Cross-domain cascade references are context only, not certified impact or operational control.
- The 9-stage runtime is a governed state machine, not nine autonomous LLM gates.
- Only the synthesis/narration stage may use grounded narration; deterministic truth path stays in code/contracts.

Never claim:
- production/public API readiness
- live autonomous monitoring
- alerts
- dispatch
- routing/control
- enforcement
- official ticket/case creation
- legal/certified/confirmed finding
- automated action
- certified citywide twin
- certified physical geometry

Current sprint remaining after Cross-Domain Cascade:
1. `MAIN-CITYBRAIN-D6-OPERATOR-DECISION-SUPPORT-SURFACE-R1`
2. `MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1`
3. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1`
4. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-FINAL-PACKAGE-REVIEW`
5. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-SPRINT-CERTIFIED-STATE-AND-HANDOVER-REFRESH`

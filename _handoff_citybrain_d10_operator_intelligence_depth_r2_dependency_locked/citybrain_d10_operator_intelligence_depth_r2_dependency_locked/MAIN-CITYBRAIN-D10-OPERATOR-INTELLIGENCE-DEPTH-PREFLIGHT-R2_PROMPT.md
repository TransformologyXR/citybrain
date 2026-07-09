# MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT-R2

## Purpose
Preflight D10 R2 with roadmap dependency corrections locked.

## Inputs to verify
- Current D9 operator cockpit freeze artifacts.
- Operator manual text gate PASS baseline.
- D9 product modes: ASK/WATCH/BRIEF/CHECK available with limitations.
- RECALL partial status.
- DIFF currently deferred/no comparable snapshots.
- Open ASK router contract-only status.
- Available city cartridges/source bundles.

## Required checks
1. Confirm D10 R2 supersedes D10 R1.
2. Confirm D10 is not an external validation/capture lane.
3. Confirm D10 will start DIFF snapshot cadence.
4. Confirm D10 will run Kit runtime probe.
5. Confirm D10 will not implement Open ASK router.
6. Confirm D10 owns selected-item investigation content only; D11 owns review-workflow state.
7. Confirm D12 consumption rule will be recorded.
8. Confirm D11 validation gate will be recorded as D14 input dependency.
9. Confirm standing D9 capability regression will run before closeout.

## Output
`outputs/main_citybrain_d10_operator_intelligence_depth_preflight_r2/D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_R2_DECISION.json`

Include:
- `status`
- `supersedes`
- `d10_scope`
- `excluded_scope`
- `dependency_locks`
- `boundary_assertions`
- `required_next_outputs`

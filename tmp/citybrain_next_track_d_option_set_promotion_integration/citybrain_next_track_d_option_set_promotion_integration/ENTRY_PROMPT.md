    You are Codex continuing CityBrain in a new lane.

    Use the attached package and the local CityBrain workspace.

    Lane:
    `Track D — Option-Set Promotion Integration`

    Start by reading:
    - `00_SHARED_CONTEXT.md`
    - `CHECKLIST.md`

    Then execute the prompt files in this order:

    1. 
# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT

Objective:
Define a bounded integration plan that maps decision-support `reviewed_option_set` / `candidate_option` objects into Track D HITL proposal lifecycle without transferring approval authority to the option-set layer.

Use as required upstreams:
- Decision-Support Sprint Certified State and Handover Refresh
- Track D HITL Reviewed Action Milestone Freeze
- Track I Inverse Dynamics Milestone Freeze
- Decision-Support Final Package Review
- Operator Decision-Support Surface R1 if present

Must establish:
- option-to-proposal mapping rules
- eligibility rules for promotion
- human promotion gate
- proposal creation fixture shape
- audit-link requirements
- rejection of automatic promotion
- rejection of execution/dispatch/control/enforcement payloads
- Track D remains authoritative for approval/rejection/modification/request-more-evidence/audit lifecycle

Must not:
- create approved proposals
- execute actions
- mutate Track D
- redefine Track D schema
- redefine `reviewed_option_set`
- create official cases/tickets
- imply dispatch, enforcement, routing/control, legal/certified finding, or automated action

Outputs:
- output root `outputs/main_citybrain_d6_track_d_option_set_promotion_integration_preflight`
- decision JSON
- upstream discovery
- integration contract plan
- option/proposal boundary audit
- no-action/no-mutation/secret/hash audits

2. 
# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-BRIDGE-R1

Objective:
Produce deterministic bridge fixtures that show how eligible candidate options can be prepared for human promotion into Track D proposal objects, while keeping all proposals unapproved and unexecuted.

Inputs:
- preflight output
- Track D proposal schema/lifecycle outputs
- reviewed option-set examples from Track S/I/Decision-Support sprint

Requirements:
- generate promotion candidate fixtures only
- preserve `option_id`, `option_set_id`, evidence refs, simulation refs, similar-case refs, cascade refs, limitation refs, and audit refs
- assign `proposal_ref = null` unless representing a pending/unapproved fixture explicitly marked not authoritative
- all fixtures must have `execution_state = not_executed`
- include do-nothing and abstain/no-safe-option cases as non-promotion or escalation cases
- include negative cases for blocked action types

Outputs:
- bridge fixture JSON/JSONL
- mapping matrix
- validation report
- claim/no-action/no-mutation/secret/hash audits

3. 
# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-GUARDRAIL-SMOKE-R2

Objective:
Prove the promotion bridge blocks unsafe or authority-crossing payloads.

Required negative tests:
- auto-approved proposal attempt blocked
- auto-execute attempt blocked
- dispatch-shaped action blocked
- routing/control-shaped action blocked
- enforcement/legal/certified finding blocked
- proposal lifecycle state written outside Track D blocked
- option set attempting to own post-promotion review state blocked
- stale scenario_state_ref flagged

Required positive tests:
- eligible review-only candidate can produce a pending human-review packet
- do-nothing baseline is preserved and not forced into action
- abstain/no-safe-option is preserved and not converted into intervention
- audit trail links to source option set and Track D lifecycle

Outputs:
- guardrail smoke report
- positive/negative fixture results
- boundary audit
- hash manifest

4. 
# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-CLOSEOUT

Objective:
Close the Track D option-set promotion integration lane.

Must verify:
- preflight PASS
- bridge R1 PASS
- guardrail smoke R2 PASS
- all JSON/JSONL parse cleanly
- hash manifests verify
- no mutations to upstream Track D or decision-support outputs
- proposal approval authority remains Track D
- no execution/dispatch/control/enforcement/legal/certified claim

Output:
- closeout decision
- acceptance matrix
- frozen boundary statement
- recommended next task

5. 
# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-MILESTONE-FREEZE

Optional freeze.

Objective:
Freeze the lane as a proposal-promotion integration contract with no execution and no authority transfer.

No new implementation. Package closeout facts, hash verification, local open index, and next recommendations.


    Do not skip ahead. Do not stage or commit unless explicitly instructed by the user.
    At the end, report final status, output root(s), runner path(s), key counts, audits, blocking/non-blocking gaps, and recommended next task.

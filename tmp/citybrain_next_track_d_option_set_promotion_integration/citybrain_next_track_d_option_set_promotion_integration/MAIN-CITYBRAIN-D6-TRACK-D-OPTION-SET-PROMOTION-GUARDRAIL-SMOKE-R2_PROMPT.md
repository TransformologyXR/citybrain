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

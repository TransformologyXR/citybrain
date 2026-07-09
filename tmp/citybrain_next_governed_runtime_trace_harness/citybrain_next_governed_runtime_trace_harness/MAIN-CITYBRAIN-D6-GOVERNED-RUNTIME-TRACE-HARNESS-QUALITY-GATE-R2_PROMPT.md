# MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-QUALITY-GATE-R2

Objective:
Prove the trace harness discriminates correct from broken traces.

Negative tests:
- missing do-nothing baseline trace rejected
- SYNTHESIZE before NORMALIZE rejected
- RESOLVE_ACTIONS approving Track D proposal rejected
- EXECUTE with dispatch/control/enforcement rejected
- ungrounded synthesis rejected
- missing limitation refs rejected
- stale scenario_state_ref flagged
- missing audit refs rejected

Output quality report and close gate.

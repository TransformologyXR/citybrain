    You are Codex continuing CityBrain in a new lane.

    Use the attached package and the local CityBrain workspace.

    Lane:
    `Governed Runtime Trace Harness`

    Start by reading:
    - `00_SHARED_CONTEXT.md`
    - `CHECKLIST.md`

    Then execute the prompt files in this order:

    1. 
# MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-PREFLIGHT

Objective:
Define a trace harness for the governed 9-stage runtime that makes each stage's input/output/audit visible without implementing a full autonomous runtime or creating new action authority.

Required upstreams:
- Decision-Support Sprint Certified State and Handover Refresh
- Governed 9-Stage Runtime Contract Smoke R1
- Track S contract spine
- Track B/R/I/C closeouts

Scope:
- trace schema
- stage IO envelope
- deterministic stage status
- single SYNTHESIZE narration boundary
- EvidenceBundle/option-set/proposal/cascade reference preservation
- negative tests for nine-LLM and agent-swarm interpretations

Not scope:
- full runtime service
- autonomous plan execution
- dispatch/control/enforcement
- production API

2. 
# MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-R1

Objective:
Generate trace fixtures for the 9 governed stages over one decision-support option set.

Stages:
RECALL
PLAN
VALIDATE_PLAN
EXECUTE
NORMALIZE
SYNTHESIZE
RESOLVE_ACTIONS
SUGGEST
COMPLETE

Rules:
- EXECUTE may only mean local simulator/optimizer/retrieval/cascade fixture execution, never real-world action.
- SYNTHESIZE is the only permitted narration stage.
- RESOLVE_ACTIONS maps to Track D proposal candidates only; no approvals.
- COMPLETE emits trace/audit/limitations only.

Output:
- trace fixture JSON/JSONL
- stage matrix
- negative tests
- validation report
- audits

3. 
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

4. 
# MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-CLOSEOUT

Objective:
Close the trace harness lane.

Verify all artifacts, hash manifests, audits, negative tests, and no-mutation. Recommend whether to proceed to runtime thin slice.


    Do not skip ahead. Do not stage or commit unless explicitly instructed by the user.
    At the end, report final status, output root(s), runner path(s), key counts, audits, blocking/non-blocking gaps, and recommended next task.

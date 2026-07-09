# MAIN-CITYBRAIN-D14-OPEN-ASK-ROUTER-IMPLEMENTATION-R1

Implement governed Open ASK router only after contract and corpus labeling pass.

Implementation may be deterministic classifier, LLM-assisted classifier, or hybrid, but it may only produce route/refusal. It must not answer.

Required tests:
- corpus route accuracy on held-out real questions
- refusal correctness for unsupported/action/legal/dispatch/prediction questions
- nearest-supported suggestions quality
- trace completeness
- no-answer text from router itself

Deliverables:
- `OPEN_ASK_ROUTER_IMPLEMENTATION_REPORT.json`
- `OPEN_ASK_ROUTER_HELDOUT_CORPUS_EVAL.json`
- updated cockpit/default text export
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.

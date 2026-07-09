# ENTRY — MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-REVIEW-WORKSPACE-R1

You are running D11, the Operator Workflow / Review Workspace sprint.

Start with the prompts in this order. Do not skip preflight. Do not create an official case/ticket/work-order object. Do not implement Open ASK. Do not implement Diff. Do not change D10 content facts except by consuming them as read-only inputs.

Sequence:
1. `MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-PREFLIGHT_PROMPT.md`
2. `MAIN-CITYBRAIN-D11-LOCAL-REVIEW-STATE-CONTRACT-R1_PROMPT.md`
3. `MAIN-CITYBRAIN-D11-REVIEW-WORKSPACE-STATE-UI-R1_PROMPT.md`
4. `MAIN-CITYBRAIN-D11-LOCAL-NOTES-AND-SESSION-SUMMARY-R1_PROMPT.md`
5. `MAIN-CITYBRAIN-D11-REVIEW-EXPORT-NONOFFICIAL-R1_PROMPT.md`
6. `MAIN-CITYBRAIN-D11-OPERATOR-GATE-TASK-PACKET-R1_PROMPT.md`
7. `MAIN-CITYBRAIN-D11-REAL-OPERATOR-SESSION-IMPORT-GATE-R1_PROMPT.md`
8. `MAIN-CITYBRAIN-D11-QUESTION-CORPUS-EXPORT-R1_PROMPT.md`
9. `MAIN-CITYBRAIN-D11-STANDING-CAPABILITY-REGRESSION-R1_PROMPT.md`
10. `MAIN-CITYBRAIN-D11-WORKFLOW-CLOSEOUT_PROMPT.md`
11. `MAIN-CITYBRAIN-D11-WORKFLOW-MILESTONE-FREEZE_PROMPT.md`

Expected non-session closeout: `PASS_D11_REVIEW_WORKSPACE_WITH_OPERATOR_GATE_PENDING` if workspace passes and no real sessions exist.
Expected session closeout: `PASS_D11_REVIEW_WORKSPACE_AND_OPERATOR_GATE_WITH_LIMITATIONS` if at least one real non-builder session is imported/scored and a question corpus is exported.

# ENTRY PROMPT — MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-REFRESHED

Run the D9 external operator validation against the refreshed D9 baseline.

Do not fabricate session records. If there are no completed non-builder session files under `inputs/d9_external_operator_sessions/`, return `PARTIAL_PENDING_OPERATOR_SESSION_RECORDS`.

Run in order:
1. `MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-PREFLIGHT`
2. `MAIN-CITYBRAIN-D9-OPERATOR-TASK-PACKET-REFRESH-R1`
3. `MAIN-CITYBRAIN-D9-OPERATOR-SESSION-IMPORT-R2`
4. `MAIN-CITYBRAIN-D9-OPERATOR-TASK-SCOREBOARD-R3`
5. `MAIN-CITYBRAIN-D9-EXTERNAL-QUESTION-CORPUS-EXPORT-R4`
6. `MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CLOSEOUT-R5`
7. `MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CERTIFIED-STATE-HANDOFF-R6`

Baseline must reference the post-hardening state:
- Recall hardening: green with limitations.
- DIFF: deferred, not a tested live mode.
- Open ASK router: contract locked, not implemented.
- D9 validation baseline refresh: green.

Required final behavior:
- With no viewer/session records: partial, not green.
- With only builder/internal records: partial internal-only.
- With at least one non-builder usable record: score the tasks and close with pass/partial depending on results.

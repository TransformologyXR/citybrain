# ENTRY PROMPT — CityBrain D8 Post-Handoff Follow-Through

Run this as one dependency-ordered Codex thread from `C:\Users\hazem\Documents\CityBrain`.

## Purpose

D8 is already green internally. This package closes the next evidence gap:

1. replace placeholder media with live captures,
2. replace internal-proxy viewer scoring with external/naive viewer evidence,
3. fix front-end depth issues surfaced by capture/viewer evidence,
4. publish a post-D8 follow-through certified-state handoff.

## Required starting point

The workspace should contain:

`outputs/main_citybrain_d8_demonstrability_certified_state_handoff`

with:

`PASS_MAIN_CITYBRAIN_D8_DEMONSTRABILITY_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS`

If not found, stop and report the missing upstream.

## Run order

1. `MAIN-CITYBRAIN-D8-LIVE-CAPTURE-MEDIA-PASS-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-LIVE-CAPTURE-TOOLCHAIN-AND-SHOT-LOCK-R1`
3. `MAIN-CITYBRAIN-D8-LIVE-OPERATOR-EXECUTIVE-CAPTURE-R2`
4. `MAIN-CITYBRAIN-D8-LIVE-MOMENT-CLIP-MANIFEST-R3`
5. `MAIN-CITYBRAIN-D8-LIVE-CAPTURE-CLAIM-AUDIT-R4`
6. `MAIN-CITYBRAIN-D8-LIVE-CAPTURE-MEDIA-PASS-CLOSEOUT`
7. `MAIN-CITYBRAIN-D8-EXTERNAL-NAIVE-VIEWER-VALIDATION-PREFLIGHT`
8. `MAIN-CITYBRAIN-D8-NAIVE-VIEWER-TEST-PACKET-R1`
9. `MAIN-CITYBRAIN-D8-NAIVE-VIEWER-SESSION-IMPORT-R2`
10. `MAIN-CITYBRAIN-D8-NAIVE-VIEWER-SCOREBOARD-R3`
11. `MAIN-CITYBRAIN-D8-EXTERNAL-NAIVE-VIEWER-VALIDATION-CLOSEOUT`
12. `MAIN-CITYBRAIN-D8-FRONTEND-DEPTH-ISSUE-REMEDIATION-PREFLIGHT`
13. `MAIN-CITYBRAIN-D8-FRONTEND-ISSUE-TRIAGE-R1`
14. `MAIN-CITYBRAIN-D8-WEB-COMPANION-DEPTH-PATCH-R2`
15. `MAIN-CITYBRAIN-D8-OMNIVERSE-KIT-DEPTH-PATCH-R3`
16. `MAIN-CITYBRAIN-D8-ONE-TRUTH-REGRESSION-R4`
17. `MAIN-CITYBRAIN-D8-FRONTEND-DEPTH-ISSUE-REMEDIATION-CLOSEOUT`
18. `MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-INTEGRATION-READINESS-REVIEW`
19. `MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-FINAL-PACKAGE-REVIEW`
20. `MAIN-CITYBRAIN-D8-POST-HANDOFF-FOLLOWTHROUGH-CERTIFIED-STATE-HANDOFF`

## Critical gates

- Do not fake media. If live captures cannot be produced, mark the media lane pending.
- Do not fake viewer sessions. If external viewer inputs are absent, produce the packet/templates and mark validation pending.
- Do not build new city/domain/perception/simulation substrate.
- Keep Mobility Access as the certified hero spine.
- Keep `execution_state = not_executed` visible and Track D authoritative.

## Reporting back

Report final statuses, output roots, media count, viewer count, P0/P1 frontend issue counts, audits, blocking gaps, and recommended next task. Do not stage or commit unless explicitly instructed.

# CityBrain D14 Route Taxonomy Repair v0.4B — Boundary Stability R1

Purpose: repair the remaining v0.4A ambiguity without changing the subject-answer architecture.

This pack is intentionally narrow. It focuses only on:
- refusal vs UI capability/help
- external action vs “can the board do X?”
- source support vs source-row profile
- EV/live/blocked claimability vs external source gap
- entity profile vs source-record profile
- context-dependency flag consistency

Do **not** add new route families. Do **not** undo `template:ask:subject_answer@v1(subject,lens)`. Do **not** run Split/Seal R3 or router preflight until the v0.4B gates pass.

Expected stop status:
`PAUSED_D14_ROUTE_TAXONOMY_V04B_AWAITING_INDEPENDENT_DOUBLE_LABELS`

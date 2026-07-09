# ENTRY PROMPT — MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-R2-DEPENDENCY-LOCKED

You are Codex operating in the CityBrain repository.

Run the D10 Operator Intelligence Depth R2 sprint.

This R2 package supersedes the earlier D10 R1 package. Follow `00_SHARED_CONTEXT.md` first.

## Goal

Make the operator cockpit materially smarter over retained city data, while locking the roadmap dependencies that must not be missed:
- Start DIFF snapshot cadence now.
- Probe Kit runtime readiness now.
- Keep D10 content work separate from D11 workflow-state work.
- Preserve external validation as a D11 exit gate, not a D10 sprint.
- Preserve D14 Open ASK dependency on real operator question corpus.

## Run order

1. `MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT-R2_PROMPT.md`
2. `MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R2_PROMPT.md`
3. `MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R2_PROMPT.md`
4. `MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2_PROMPT.md`
5. `MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R2_PROMPT.md`
6. `MAIN-CITYBRAIN-D10-SELECTED-ITEM-INVESTIGATION-CONTENT-R2_PROMPT.md`
7. `MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R2_PROMPT.md`
8. `MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-START-R2_PROMPT.md`
9. `MAIN-CITYBRAIN-D10-KIT-RUNTIME-PROBE-R0_PROMPT.md`
10. `MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R2_PROMPT.md`
11. `MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R2_PROMPT.md`
12. `MAIN-CITYBRAIN-D10-D9-CAPABILITY-REGRESSION-RERUN-R2_PROMPT.md`
13. `MAIN-CITYBRAIN-D10-ROADMAP-DEPENDENCY-HANDOFF-R2_PROMPT.md`
14. `MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-CLOSEOUT-R2_PROMPT.md`
15. `MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-MILESTONE-FREEZE-R2_PROMPT.md`

## Do not do

- Do not run external operator validation in D10.
- Do not fabricate operator sessions or question corpus.
- Do not implement Open ASK router.
- Do not claim live DIFF.
- Do not build D13 Kit/Omniverse feature work; only run the runtime/environment probe.
- Do not implement D11 lifecycle state except where needed as existing local verb proof.
- Do not add datasets without tying them to a consuming WATCH query, ASK template, or RECALL matcher.
- Do not create official cases, tickets, alerts, dispatches, routes, controls, enforcement actions, legal findings, or certified findings.

## Final status expectations

Acceptable:
- `PASS_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R2_WITH_LIMITATIONS`
- `PASS_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R2_PARTIAL_KIT_PROBE_BLOCKED_WITH_LIMITATIONS`
- `PARTIAL_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R2_DATA_GAPS_EXPLICIT`

Not acceptable:
- Any Open ASK implementation without real operator question corpus.
- Any DIFF live/change claim without comparable snapshots.
- Any validation pass based on fabricated sessions.
- Any broad data landing without a consuming product mode.

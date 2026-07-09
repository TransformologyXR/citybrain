# ENTRY PROMPT — D9 Ask / Watch / Brief / Check Runtime R1

You are Codex operating in `C:\Users\hazem\Documents\CityBrain`.

Run the D9 product-mode runtime implementation in the following sequence.

Do not stage or commit unless explicitly asked.

## Sequence

1. `MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-PREFLIGHT`
2. `MAIN-CITYBRAIN-D9-PRODUCT-MODE-CONTRACT-R1`
3. `MAIN-CITYBRAIN-D9-PRODUCT-MODE-RUNTIME-BUNDLE-R2`
4. `MAIN-CITYBRAIN-D9-ASK-CITED-ANSWER-RUNTIME-R3`
5. `MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-QUEUE-R4`
6. `MAIN-CITYBRAIN-D9-BRIEF-PACKET-GENERATOR-R5`
7. `MAIN-CITYBRAIN-D9-CHECK-GUARDRAIL-AND-SOURCE-DEPTH-R6`
8. `MAIN-CITYBRAIN-D9-RECALL-CUTAWAY-R7`
9. `MAIN-CITYBRAIN-D9-WEB-PRODUCT-MODE-CONSOLE-R8`
10. `MAIN-CITYBRAIN-D9-PRODUCT-MODE-RUNTIME-GUARDRAIL-SMOKE-R9`
11. `MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-CLOSEOUT`
12. `MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-MILESTONE-FREEZE`

## Inputs

Use the two D9 data-scout closeouts if present:

- `outputs/main_citybrain_d9_data_scout_closeout`
- `outputs/main_citybrain_d9_broad_data_scout_closeout`
- `outputs/main_citybrain_d9_broad_data_scout_milestone_freeze`

Also consume existing D8 story queue/scenario sources.

## Hard gates

- No Diff implementation except deferred ledger.
- No Perception/VSS implementation except deferred ledger.
- No production/public API claim.
- No live monitoring/alerting.
- No dispatch/routing/control/enforcement.
- No official ticket/case creation.
- No legal/certified finding.
- No automated action.
- `execution_state = not_executed` must remain visible wherever action-shaped ideas appear.

## Expected final status

`PASS_MAIN_CITYBRAIN_D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_WITH_LIMITATIONS`

If Ask/Watch/Brief/Check cannot be made useful from the inputs, return a partial with exact blocker ledgers rather than generating a fake product console.

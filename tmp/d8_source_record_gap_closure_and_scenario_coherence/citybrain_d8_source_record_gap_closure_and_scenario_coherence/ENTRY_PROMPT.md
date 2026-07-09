# ENTRY PROMPT — CityBrain D8 Source Record Gap Closure & Scenario Coherence

You are running the D8 source-record gap closure and scenario-coherence lane.

Start from the current CityBrain workspace. Do not stage or commit. Preserve existing unrelated dirty/untracked files.

Run the prompts in this order:

1. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-D7-MEDIA-OBSERVATION-SOURCE-RECORD-PACK-R1`
3. `MAIN-CITYBRAIN-D8-GUARDRAIL-REFUSAL-REVIEW-LOG-PACK-R1`
4. `MAIN-CITYBRAIN-D8-HUMAN-REVIEW-STOP-RECORD-PACK-R1`
5. `MAIN-CITYBRAIN-D8-LONDON-MOBILITY-CORRIDOR-COHERENCE-REVIEW-R1`
6. `MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-GAP-CLOSURE-UI-INTEGRATION-R2`
7. `MAIN-CITYBRAIN-D8-CITY-FACT-VIEWER-READINESS-REVIEW-R3`
8. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-CLOSEOUT`
9. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-MILESTONE-FREEZE`

Success means:
- M13/M07/M08 blockers are either resolved with real records or explicitly preserved as blockers.
- The UI no longer implies unrelated source cards are the same scenario.
- The viewer-readiness decision is honest: GO, CONDITIONAL_GO, or NO_GO.
- All boundary, no-action, no-mutation, secret, hash, and no-fact-invention audits pass.

Do not claim external viewer readiness unless the source-record blockers are resolved or consciously accepted as visible, non-demo-blocking limitations.

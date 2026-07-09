# ENTRY PROMPT — D8 NYC Cascade Scenario Layer Authoring R1

Run the following tasks in order. Do not run UI redesign, capture, viewer validation, or new source landing from this pack.

1. `MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-NYC-FLOW3-HERO-EVIDENCE-EXTRACTION-R1`
3. `MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-AUTHORING-R2`
4. `MAIN-CITYBRAIN-D8-NYC-CASCADE-SOURCE-EVIDENCE-MAP-R3`
5. `MAIN-CITYBRAIN-D8-NYC-CASCADE-REVIEW-OPTIONS-BOUNDARY-R4`
6. `MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-QUEUE-INTEGRATION-R5`
7. `MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-CLOSEOUT`
8. `MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-MILESTONE-FREEZE`

Acceptance rule:
- A concrete NYC cascade scenario must name the actual source-backed event/record(s), affected asset/context records, evidence refs, uncertainty, review choices, and human stop.
- If it cannot do that from existing outputs, do not fabricate. Return partial with a gap ledger.

Do not mutate prior certified outputs. New source files may be added under `packages/fixtures/story_first_demo/` or a new scenario-specific fixture folder. Runner/output roots must be additive.

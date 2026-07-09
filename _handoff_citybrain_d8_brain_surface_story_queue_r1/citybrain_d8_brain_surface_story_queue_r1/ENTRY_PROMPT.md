# ENTRY PROMPT — D8 Brain Surface Story Queue R1

You are running the D8 Brain Surface Story Queue R1 lane.

Goal:
Turn the validated London Wood Lane and NYC MVC cascade scenario layers into a navigable story queue surface. Do not author new city facts. Do not add new data. Do not run external viewer validation. Do not build a raw record gallery.

Run in this exact order:

1. `MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-STORY-QUEUE-CONTRACT-R1`
3. `MAIN-CITYBRAIN-D8-TWO-STORY-SOURCE-BUNDLE-INTEGRATION-R2`
4. `MAIN-CITYBRAIN-D8-WEB-BRAIN-SURFACE-STORY-QUEUE-R3`
5. `MAIN-CITYBRAIN-D8-STORY-DRILLDOWN-AND-WOVEN-MOMENTS-R4`
6. `MAIN-CITYBRAIN-D8-CROSS-STORY-NAVIGATION-AND-CUTAWAY-SMOKE-R5`
7. `MAIN-CITYBRAIN-D8-BRAIN-SURFACE-DOM-AND-HUMAN-SMOKE-R6`
8. `MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-CLOSEOUT`
9. `MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-MILESTONE-FREEZE`

Hard gates:
- Default UI must open on a queue of stories, not records.
- At least two primary story cards must render if both scenario layers are present.
- Each primary story card must show a different `story_query_id@version`.
- London duplicate proximity stories must not count as distinct stories.
- Drilldown must show: situation, source records, tension, intelligence beat, review-only options, uncertainty, human stop, limitations.
- Trust moments are woven inside story drilldowns; they are not standalone stories.
- Chicago/Helsinki cutaways are optional/woven; they must not replace primary stories.
- No overclaim: especially no EV blocked/available/unavailable claim, no certified affected-building truth, no dispatch/routing/control/enforcement/legal/action claim.

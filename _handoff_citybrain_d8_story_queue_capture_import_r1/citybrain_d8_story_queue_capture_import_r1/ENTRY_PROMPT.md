# ENTRY PROMPT — MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-IMPORT-R1

You are working in `C:\Users\hazem\Documents\CityBrain`.

Run this pack in order. This is a media/capture validation lane for the already-frozen D8 two-story brain surface queue.

Do not perform UI redesign, story authoring, or data landing. Do not stage or commit.

Sequence:
1. `MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-IMPORT-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-STORY-QUEUE-REAL-MEDIA-IMPORT-R1`
3. `MAIN-CITYBRAIN-D8-STORY-QUEUE-MEDIA-COVERAGE-SMOKE-R2`
4. `MAIN-CITYBRAIN-D8-STORY-QUEUE-MEDIA-CLAIM-AUDIT-R3`
5. `MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-CLOSEOUT-R4`
6. `MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-HANDOFF-R5`

Input media should be under:
`inputs/d8_story_queue_media/`

If the user has captured files somewhere else, search only reasonable local project paths such as `inputs/`, `outputs/`, `Desktop`, `Downloads`, or the browser save location, but do not copy arbitrary unrelated files. Record exactly what was imported.

Truthful statuses:
- If real media exists and covers both stories + boundary: `PASS_MAIN_CITYBRAIN_D8_STORY_QUEUE_CAPTURE_HANDOFF_R5_WITH_VIEWER_PENDING`
- If media exists but coverage is incomplete: `PARTIAL_MEDIA_COVERAGE_GAPS_MAIN_CITYBRAIN_D8_STORY_QUEUE_CAPTURE_HANDOFF_R5`
- If no real media exists: `PARTIAL_PENDING_MEDIA_MAIN_CITYBRAIN_D8_STORY_QUEUE_CAPTURE_HANDOFF_R5`

Viewer validation is out of scope unless real viewer records already exist under `inputs/d8_story_queue_viewer_records/`; do not claim external validation without them.

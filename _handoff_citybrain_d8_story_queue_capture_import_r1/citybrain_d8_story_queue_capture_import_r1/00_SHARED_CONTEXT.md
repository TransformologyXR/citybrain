# CityBrain D8 — Story Queue Capture Import R1 Shared Context

Current baseline:
- `PASS_MAIN_CITYBRAIN_D8_BRAIN_SURFACE_STORY_QUEUE_MILESTONE_FREEZE_WITH_LIMITATIONS`
- Web brain surface opens as a queue-first interface, not a source-record gallery.
- Primary stories rendered: 2
- Distinct story-query versions: 2
  - London Wood Lane: `story-query:proximity_works_to_access@v1`
  - NYC MVC cascade: `story-query:incident_to_affected_asset_response_cascade@v1`
- Duplicate London same-shape stories excluded: 3
- Boundary remains local/replay/review-only; `execution_state = not_executed`.

This pack is for real media import and claim audit after the user has captured screenshots/clips of the two-story queue.

Do not redesign UI here. Do not author new stories. Do not mutate source story fixtures. Import media, validate coverage, audit claims, and close truthfully.

Expected local input folder:
`inputs/d8_story_queue_media/`

Accepted media:
- `.png`, `.jpg`, `.jpeg`, `.webp`
- `.mp4`, `.mov`, `.webm`
- optional `media_manifest.json`

If no real media exists, return partial. If media exists but does not cover both primary stories and boundary labels, return partial with gap ledger. If viewer records are absent, do not claim external viewer validation.

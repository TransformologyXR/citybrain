# MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-IMPORT-PREFLIGHT

Goal: confirm the story queue baseline is available before importing media.

Required checks:
- Locate the latest `main_citybrain_d8_brain_surface_story_queue_milestone_freeze` output root.
- Confirm milestone freeze PASS with limitations.
- Confirm exactly two counted primary stories unless the freeze explicitly records a newer count.
- Confirm distinct story-query versions include:
  - `story-query:proximity_works_to_access@v1`
  - `story-query:incident_to_affected_asset_response_cascade@v1`
- Confirm duplicate London same-shape stories were excluded.
- Confirm UI mode is queue-first and not record-gallery fallback.

Output root:
`outputs/main_citybrain_d8_story_queue_capture_import_preflight`

Artifacts:
- `PREFLIGHT_DECISION.json`
- `INPUT_BASELINE_INDEX.json`
- `CAPTURE_INPUT_EXPECTATIONS.md`
- `LOCAL_OPEN_INDEX.md`
- `HASH_MANIFEST.json`

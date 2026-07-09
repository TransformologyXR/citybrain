# MAIN-CITYBRAIN-D8-STORY-QUEUE-MEDIA-COVERAGE-SMOKE-R2

Goal: verify the captured media covers the two-story queue and not just a single page fragment.

Coverage requirements:
1. Queue overview visible.
2. London Wood Lane story visible.
3. NYC MVC cascade story visible.
4. At least one story drilldown or detail panel visible.
5. Human review/no-action boundary visible.
6. No overclaim text visible or implied.

Preferred but not mandatory:
- Cross-story navigation visible.
- Woven trust moment visible.
- Capability/cutaway affordance visible.

If image OCR or DOM snapshot is unavailable, use filenames + manifest + any available HTML/screenshot metadata, but record confidence honestly.

Output root:
`outputs/main_citybrain_d8_story_queue_media_coverage_smoke_r2`

Artifacts:
- `MEDIA_COVERAGE_SMOKE_DECISION.json`
- `STORY_COVERAGE_MATRIX.json`
- `BOUNDARY_VISIBILITY_MATRIX.json`
- `MEDIA_GAP_LEDGER.json`
- `LOCAL_OPEN_INDEX.md`
- `HASH_MANIFEST.json`

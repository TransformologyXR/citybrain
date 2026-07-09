# MAIN-CITYBRAIN-D8-STORY-QUEUE-REAL-MEDIA-IMPORT-R1

Goal: import real screenshots/clips captured by the user for the story queue surface.

Input folder:
`inputs/d8_story_queue_media/`

Accepted files: PNG/JPG/JPEG/WEBP/MP4/MOV/WEBM.

Reject:
- README/template files as media.
- generated JSON reports as media.
- placeholder manifests with no files.
- old one-story or source-record gallery captures unless they are explicitly marked as comparison/legacy and not counted for current coverage.

If `media_manifest.json` exists, validate it. If absent, create a derived manifest from discovered media files.

Classify each imported file by visible evidence if possible:
- story queue overview
- London Wood Lane drilldown/story card
- NYC MVC cascade drilldown/story card
- review options/human stop
- boundary/limitations
- cross-story navigation/cutaway

Output root:
`outputs/main_citybrain_d8_story_queue_real_media_import_r1`

Artifacts:
- `REAL_MEDIA_IMPORT_DECISION.json`
- `IMPORTED_MEDIA_MANIFEST.json`
- `MEDIA_FILE_HASHES.json`
- `REJECTED_MEDIA_CANDIDATES.json`
- `MEDIA_COVERAGE_PRELIMINARY.json`
- `LOCAL_OPEN_INDEX.md`
- `HASH_MANIFEST.json`

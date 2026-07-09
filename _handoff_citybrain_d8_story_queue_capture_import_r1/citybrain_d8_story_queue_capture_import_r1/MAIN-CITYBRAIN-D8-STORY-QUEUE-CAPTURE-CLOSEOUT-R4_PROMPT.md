# MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-CLOSEOUT-R4

Goal: close the media capture lane truthfully.

Summarize:
- media_count
- story coverage count
- coverage gaps
- overclaim count
- boundary audit status
- whether viewer validation remains pending

Status logic:
- PASS_WITH_VIEWER_PENDING if media covers both stories and audits pass, but no viewer records.
- PARTIAL_MEDIA_COVERAGE_GAPS if media is real but incomplete.
- PARTIAL_PENDING_MEDIA if no media.
- FAIL only for boundary/overclaim/secret/no-mutation failure.

Output root:
`outputs/main_citybrain_d8_story_queue_capture_closeout_r4`

Artifacts:
- `STORY_QUEUE_CAPTURE_CLOSEOUT_DECISION.json`
- `CAPTURE_CLOSEOUT_SUMMARY.md`
- `CURRENT_CAPTURE_TRUTH_REGISTER.json`
- `READY_NEXT_VIEWER_VALIDATION.md`
- `LOCAL_OPEN_INDEX.md`
- `HASH_MANIFEST.json`

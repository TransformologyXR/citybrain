# MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-HANDOFF-R5

Goal: produce the final handoff for the story-queue media capture lane.

Include:
- selected stories and query IDs
- media coverage status
- viewer validation status
- limitations
- exact next task recommendation

If viewer records are missing, recommend:
`MAIN-CITYBRAIN-D8-STORY-QUEUE-VIEWER-SESSION-R1`

Output root:
`outputs/main_citybrain_d8_story_queue_capture_handoff_r5`

Artifacts:
- `STORY_QUEUE_CAPTURE_HANDOFF_DECISION.json`
- `HANDOFF_BRIEF.md`
- `MEDIA_IMPORT_INDEX.json`
- `VIEWER_VALIDATION_PENDING_LEDGER.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `LOCAL_OPEN_INDEX.md`
- `HASH_MANIFEST.json`

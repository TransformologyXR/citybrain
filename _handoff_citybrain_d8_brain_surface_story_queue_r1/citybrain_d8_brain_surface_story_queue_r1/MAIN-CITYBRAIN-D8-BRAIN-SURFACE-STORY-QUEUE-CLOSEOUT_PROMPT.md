# MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-CLOSEOUT

Close out the brain surface story queue lane.

Closeout must state:
- number of primary stories rendered
- story-query distinct count
- whether London + NYC both render
- whether duplicate London shapes were excluded
- whether UI is queue-first or record-gallery-like
- whether any story overclaims beyond source evidence
- capture/viewer readiness status
- next recommended task

Acceptable statuses:
- `PASS_MAIN_CITYBRAIN_D8_BRAIN_SURFACE_STORY_QUEUE_CLOSEOUT_WITH_LIMITATIONS`
- `PARTIAL_BRAIN_SURFACE_QUEUE_ONLY_ONE_STORY_RENDERED`
- `FAIL_RECORD_GALLERY_REGRESSION`
- `FAIL_STORY_OVERCLAIM`

Produce:
- `BRAIN_SURFACE_STORY_QUEUE_CLOSEOUT_DECISION.json`
- `CURRENT_BRAIN_SURFACE_TRUTH_REGISTER.json`
- `BLOCKERS_AND_NEXT_ACTIONS.md`
- audits and hash manifest

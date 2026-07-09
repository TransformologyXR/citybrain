# MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-QUEUE-INTEGRATION-R5

Create:
`outputs/main_citybrain_d8_nyc_cascade_story_queue_integration_r5`

Do not patch UI. Produce a story-queue integration candidate that future UI work can consume.

Inputs:
- Wood Lane scenario layer
- NYC cascade scenario layer if green
- deep story inventory role portfolio

Produce:
- `DISTINCT_PRIMARY_QUEUE_CANDIDATE_R2.json`
- `STORY_QUERY_DISTINCTNESS_AUDIT.json`
- `WOVEN_CUTAWAY_PLAN_FOR_NYC_CASCADE.json`
- `TRUST_MOMENT_WEAVING_PLAN_FOR_NYC_CASCADE.json`
- `UI_REQUIREMENTS_DELTA_NO_CODE.md`
- audits/hash manifest

Distinctness rule:
- Wood Lane uses `story-query:proximity_works_to_access@v1`.
- NYC must use `story-query:incident_to_affected_asset_response_cascade@v1`.
- If NYC cannot become concrete, mark it `still_authoring_plan_only` and do not count it as primary.

# MAIN-CITYBRAIN-D8-NYC-CASCADE-STORY-AUTHORING-R2

Create:
`outputs/main_citybrain_d8_nyc_cascade_story_authoring_r2`

Using R1 evidence only, author a bounded scenario layer for:
`story-query:incident_to_affected_asset_response_cascade@v1`

A valid scenario layer must include:
- `story_id`
- `story_title`
- `story_query_id`
- `version`
- `specific_subject`
- `review_premise`
- `tension`
- `source_records`
- `affected_asset_or_context_records`
- `intelligence_beat`
- `uncertainty`
- `review_only_choices`
- `human_stop`
- `limitations`
- `forbidden_claims`

Allowed language:
- "records suggest context for human review"
- "the system links an incident/context record to affected-asset context"
- "needs human review"
- "no action taken"

Forbidden unless directly proven:
- "caused"
- "confirmed impact"
- "affected building/route/service"
- "emergency response delayed"
- "route should be changed"
- "dispatch/enforce/control"

Produce:
- `NYC_CASCADE_SCENARIO_LAYER.json`
- `NYC_CASCADE_SCENARIO_NARRATIVE.md`
- `SCENARIO_AUTHORING_DECISION.json`
- `NO_FACT_INVENTION_AUDIT.json`
- standard audits/hash manifest

If evidence is insufficient for a concrete layer, produce `NYC_CASCADE_SCENARIO_LAYER_GAP_LEDGER.json` and return partial, not green.

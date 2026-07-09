# MAIN-CITYBRAIN-D8-STORY-QUEUE-CONTRACT-R1

Define the story queue contract before UI work.

Create a versioned contract for a story queue item:
- `story_id`
- `title`
- `city`
- `role = primary_story`
- `story_query_id`
- `query_version`
- `tension`
- `specific_subject`
- `source_record_refs`
- `intelligence_beat`
- `review_options_summary`
- `trust_moments_available`
- `cutaways_available`
- `boundary_summary`
- `not_claimed`
- `viewer_readiness_status`

Distinctness gate:
- counted primary stories must not share the same `story_query_id@version`.
- if they do, mark lower-priority duplicates as `duplicate_shape_not_counted`.

Produce:
- `STORY_QUEUE_CONTRACT_SCHEMA.json`
- `STORY_QUERY_DISTINCTNESS_RULES.json`
- `STORY_QUEUE_ACCEPTANCE_CRITERIA.json`

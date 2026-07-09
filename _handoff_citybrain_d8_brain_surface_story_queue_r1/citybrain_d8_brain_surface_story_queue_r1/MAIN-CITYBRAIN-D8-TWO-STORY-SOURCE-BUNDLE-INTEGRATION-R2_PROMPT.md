# MAIN-CITYBRAIN-D8-TWO-STORY-SOURCE-BUNDLE-INTEGRATION-R2

Build a read-only integrated queue bundle from the frozen London and NYC story layers.

Required queue stories:
1. London Wood Lane access review
2. NYC MVC cascade review

Do not include Warwick/Lancaster/Claps as primary stories if they share the Wood Lane proximity query. They may appear in a "same-shape examples / parked" section if needed.

For each story, include:
- source records and evidence map
- story beats
- uncertainty fields
- review options
- human stop
- limitation ledger
- capability cutaway slots (Chicago/Helsinki) if already validated
- trust moments (refusal, review stop, no-action, uncertainty)

Produce:
- `BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json`
- `PRIMARY_STORY_QUEUE.json`
- `DUPLICATE_SHAPE_NOT_COUNTED_LEDGER.json`
- `WOVEN_TRUST_AND_CUTAWAY_MAP.json`
- `QUEUE_BUNDLE_VALIDATION_REPORT.json`

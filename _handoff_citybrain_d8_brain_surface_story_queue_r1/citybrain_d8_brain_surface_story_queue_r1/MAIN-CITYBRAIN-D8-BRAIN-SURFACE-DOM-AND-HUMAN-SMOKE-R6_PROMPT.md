# MAIN-CITYBRAIN-D8-BRAIN-SURFACE-DOM-AND-HUMAN-SMOKE-R6

Launch or statically render the web page and prove the UI is story-first.

DOM assertions:
- London story title appears.
- NYC story title appears.
- both story_query_id values are present in hidden/assertion data or technical section.
- no default card uses raw fixture IDs as primary text.
- no default top section is a source-record inventory.
- default DOM contains fewer record cards than story/story-drilldown cards or otherwise proves queue-first layout.
- boundary phrase "no action" or equivalent appears once per story, not boilerplate repeated on every source row.

Human-smoke proxy:
- create `HUMAN_SMOKE_REVIEW.md` that answers:
  1. Can a viewer name the two situations?
  2. Can a viewer tell how they differ?
  3. Can a viewer find why no action is taken?
  4. Can a viewer find supporting records without being flooded by them?
  5. Does the page still feel like an inventory?

Produce:
- `BRAIN_SURFACE_DOM_ASSERTION_REPORT.json`
- `BRAIN_SURFACE_SCREENSHOT_OR_DOM_CAPTURE.html`
- `HUMAN_SMOKE_REVIEW.md`
- `BRAIN_SURFACE_VIEWER_READINESS_STATUS.json`

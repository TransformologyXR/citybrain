# MAIN-CITYBRAIN-D8-CROSS-STORY-NAVIGATION-AND-CUTAWAY-SMOKE-R5

Add navigation and smoke tests.

Required navigation:
- queue -> story drilldown
- story drilldown -> evidence
- story drilldown -> review options
- story drilldown -> limitations/human stop
- optional story drilldown -> Chicago precedent cutaway
- optional story drilldown -> Helsinki visual pick cutaway

Smoke tests:
- selecting London does not show NYC facts.
- selecting NYC does not show London EV availability/blockage claims.
- cutaways never become primary stories.
- duplicate-shape London stories remain outside counted primary queue.
- boundary labels remain visible once per story.

Produce:
- `CROSS_STORY_NAVIGATION_SMOKE_REPORT.json`
- `CUTAWAY_BOUNDARY_SMOKE_REPORT.json`
- `STORY_CONTEXT_ISOLATION_REPORT.json`

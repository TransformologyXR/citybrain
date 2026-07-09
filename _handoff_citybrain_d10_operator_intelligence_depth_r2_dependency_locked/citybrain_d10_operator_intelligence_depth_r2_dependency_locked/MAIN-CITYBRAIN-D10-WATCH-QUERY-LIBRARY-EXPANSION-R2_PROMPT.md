# MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2

## Purpose
Expand WATCH queries so the patch board has more useful intelligence.

## Query requirements
Each query must have:
- `query_id`
- version
- operator title
- input fields
- required source fields
- result schema
- why this needs review
- false-positive / may-be-nothing reason
- suggested human check
- admission class
- golden match
- designed non-match
- no-action boundary

## Candidate query families
- works near access asset
- source-depth gap
- stale record
- cross-source disagreement
- low-confidence link
- incident near candidate asset context
- recurring pattern review
- missing address/name link
- evidence-strength change candidate (DIFF-ready only, no live claim)
- visual identity link gap (parked unless tied to D13)

## Boundaries
- WATCH lists review candidates, not alerts.
- No notification/dispatch/urgency-as-finding.
- Ranking surfaces attention, not authority.

## Output
`WATCH_QUERY_LIBRARY_EXPANSION_R2.json`

Also update any local artifacts needed for D10 patch board if safe.

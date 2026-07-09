# MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R2

## Purpose
Smoke deterministic city-data search and ASK/refusal behavior after D10 changes.

## Required smokes
- supported selected-item question
- source-record support question
- uncertainty question
- cannot-claim question
- entity lookup where available
- held-out supported query from retained data
- out-of-scope unsupported query with clean refusal
- action/legal/dispatch/prediction seeking requests refuse or route to boundary explanation
- no unsupported facts/citations

## Output
`ASK_SEARCH_AND_REFUSAL_SMOKE_R2.json`

## Hard boundary
No Open ASK router implementation.
No model answer generation.

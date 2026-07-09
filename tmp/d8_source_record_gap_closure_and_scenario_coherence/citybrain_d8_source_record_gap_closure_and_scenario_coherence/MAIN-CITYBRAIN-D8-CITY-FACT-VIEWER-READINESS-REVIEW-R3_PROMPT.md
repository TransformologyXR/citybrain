# MAIN-CITYBRAIN-D8-CITY-FACT-VIEWER-READINESS-REVIEW-R3

Goal: decide whether the source-backed UI is ready for internal capture and/or external naive-viewer validation.

Inputs:
- UI integration R2 output.
- city fact DOM assertion report.
- all source-record gap pack decisions.
- London coherence verdict.

Return one of:
- `GO_EXTERNAL_VIEWER_VALIDATION`
- `CONDITIONAL_GO_INTERNAL_CAPTURE_ONLY`
- `NO_GO_SOURCE_DEPTH_OR_SCENARIO_COHERENCE`

Criteria for external viewer GO:
- default UI has enough actual city/source-derived records to explain a scenario or deliberately frames itself as a source-record portfolio.
- no default UI overclaims scenario linkage.
- M13/M07/M08 either resolved or explicitly accepted as non-blocking known gaps.
- 0 forbidden fixture-label hits in default DOM.
- boundary/no-action visible.

Produce:
- `CITY_FACT_VIEWER_READINESS_REVIEW_R3_DECISION.json`
- `VIEWER_GO_NO_GO_MATRIX.json`
- `CAPTURE_SCOPE_RECOMMENDATION.md`
- `OPEN_GAPS_IF_ANY.json`
- `HASH_MANIFEST.json`

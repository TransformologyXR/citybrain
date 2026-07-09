# MAIN-CITYBRAIN-D9-DATA-SCOUT-CLOSEOUT

Create output root:
`outputs/main_citybrain_d9_data_scout_closeout`

Reconcile all scout outputs.

Produce:
- D9_MODE_DATA_READINESS_MATRIX.json
- D9_MODE_SURFACE_CANDIDATE_CATALOG.json
- D9_PRODUCT_MODE_BUILD_RECOMMENDATION.md
- D9_READY_NOW_MODES.json
- D9_PARTIAL_MODES.json
- D9_BLOCKED_MODES.json
- D9_DATA_SCOUT_CLOSEOUT_DECISION.json

Recommended decision values:
- GO_D9_ASK_WATCH_BRIEF_WITH_LIMITATIONS
- GO_D9_ASK_BRIEF_ONLY_WATCH_PARTIAL
- PARTIAL_FILL_DATA_GAPS_BEFORE_D9
- NO_GO_PRODUCT_MODE_INPUTS_TOO_THIN

Acceptance:
- PASS if recommendation is evidence-backed and no mode is overstated.

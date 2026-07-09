# ENTRY PROMPT — D9 Preflight Data Scout for Product Modes

Run this pack before the D9 Product Modes Ask/Watch/Brief runtime pack.

Goal: determine what D9 can honestly surface in ASK, WATCH, RECALL, BRIEF, CHECK, and DIFF modes from the current D8 story queue, source-record bundles, story scenario layers, and output ledger.

Run sequence:

1. MAIN-CITYBRAIN-D9-DATA-SCOUT-PREFLIGHT
2. MAIN-CITYBRAIN-D9-MODE-SURFACE-INPUT-INVENTORY-R1
3. MAIN-CITYBRAIN-D9-ASK-QUESTION-COVERAGE-SCOUT-R2
4. MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-POTENTIAL-R3
5. MAIN-CITYBRAIN-D9-RECALL-PRECEDENT-COVERAGE-R4
6. MAIN-CITYBRAIN-D9-BRIEF-PACKET-READINESS-R5
7. MAIN-CITYBRAIN-D9-CHECK-DIFF-DATA-QUALITY-CHANGE-SCOUT-R6
8. MAIN-CITYBRAIN-D9-PRODUCT-MODE-SOURCE-GAP-LEDGER-R7
9. MAIN-CITYBRAIN-D9-DATA-SCOUT-CLOSEOUT
10. MAIN-CITYBRAIN-D9-DATA-SCOUT-MILESTONE-FREEZE

Hard requirements:
- Do not edit web app, Kit extension, story fixtures, source bundles, or certified outputs.
- Do not run D9 product-mode implementation.
- Do not land new external data unless already present locally; this is a scout over available project data.
- Every mode claim must map to concrete records, story layers, evidence bundles, trace records, or explicit blockers.
- Return PARTIAL for any mode that lacks source depth.

Expected final outputs:
- D9_MODE_DATA_READINESS_MATRIX.json
- D9_MODE_SURFACE_CANDIDATE_CATALOG.json
- D9_ASK_ANSWERABILITY_MATRIX.json
- D9_WATCH_QUERY_CANDIDATE_REGISTRY.json
- D9_RECALL_PRECEDENT_READINESS.json
- D9_BRIEF_READINESS_MATRIX.json
- D9_CHECK_DIFF_OPPORTUNITY_LEDGER.json
- D9_SOURCE_GAP_LEDGER.json
- D9_PRODUCT_MODE_BUILD_RECOMMENDATION.md

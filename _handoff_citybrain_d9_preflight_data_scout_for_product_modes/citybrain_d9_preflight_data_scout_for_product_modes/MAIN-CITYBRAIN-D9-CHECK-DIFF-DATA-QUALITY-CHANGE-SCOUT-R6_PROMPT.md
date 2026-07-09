# MAIN-CITYBRAIN-D9-CHECK-DIFF-DATA-QUALITY-CHANGE-SCOUT-R6

Create output root:
`outputs/main_citybrain_d9_check_diff_scout_r6`

Scout CHECK and DIFF modes.

CHECK candidates:
- source-depth blockers: D7 media observation detail missing, refusal log missing, viewer records missing.
- low-confidence/proximity-only joins: Wood Lane works near EV asset; not causality.
- candidate affected asset limitations: NYC cascade candidate tax-lot context not certified affected-building truth.
- duplicate story shapes: London same-query candidates not counted as primary stories.
- Kit runtime/capture limitations if still present.

DIFF candidates:
- presence of repeated snapshots or timestamped output roots that can support change since last run.
- story queue evolution: one story -> two-story queue -> capture pending.
- source records with update timestamps if present.

Produce:
- CHECK_CANDIDATE_LEDGER.json
- CHECK_QUERY_PROTOTYPES.json
- DIFF_READINESS_MATRIX.json
- DIFF_UNSUPPORTED_LEDGER.json
- CHECK_DIFF_SCOUT_DECISION.json

Acceptance:
- PASS if CHECK has at least 5 meaningful product-grade checks and DIFF is classified honestly.
- PARTIAL if DIFF lacks source cadence but CHECK is strong.

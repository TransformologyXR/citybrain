# MAIN-CITYBRAIN-D9-RECALL-PRECEDENT-COVERAGE-R4

Create output root:
`outputs/main_citybrain_d9_recall_precedent_coverage_r4`

Scout RECALL mode: what can CityBrain honestly recall as similar or precedent context?

Inputs:
- Chicago similar-case source bundle.
- Deep story inventory Chicago candidate outputs.
- Any similar-case attachments already present in Wood Lane/NYC story queue.

For each recall candidate:
- source city and dataset
- record id
- case summary if present
- match reason specificity
- whether it is specific enough to be surfaced in a viewer/product mode
- limitation / not-instruction statement

Classify:
- RECALL_READY_SPECIFIC_MATCH
- RECALL_PARTIAL_GENERIC_MATCH
- RECALL_BACKLOG_NEEDS_MATCH_REASON

Produce:
- RECALL_PRECEDENT_CANDIDATE_TABLE.json
- RECALL_MATCH_REASON_QUALITY_REPORT.json
- RECALL_READY_EXEMPLARS.json
- RECALL_BACKLOG_LEDGER.json
- RECALL_SCOUT_DECISION.json

Acceptance:
- PASS if at least 2 precedents have specific match reasons.
- PARTIAL if only generic Chicago memory is available.
